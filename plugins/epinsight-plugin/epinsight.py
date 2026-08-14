##
## Load the deep learning model
##
import io
import os
import sys
import json
import shutil
import tempfile
import time
import uuid
from zipfile import ZipFile
import glob
import subprocess
import base64

import orthanc
from notifications import JobNotification

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

sys.path.append(os.path.join(SCRIPT_DIR, ".."))


class EPINSIGHTRunner:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.input_dir = None
        self.mni_template_path = None
        self.uuid = None
        self.output_paths = None
        self.name = "Epinsight"

    def _create_input(self, dicom: ZipFile):
        self.uuid = uuid.uuid4().hex
        self.input_dir = os.path.join(self.temp_dir, self.uuid, "input")
        dicom.extractall(self.input_dir)

    def clean_up(self):
        if self.uuid:
            shutil.rmtree(os.path.join(self.temp_dir, self.uuid), ignore_errors=True)

    def run(self, dicom: ZipFile, user_id: str, study_id: str, patient_name: str, patient_id: str):
        self._create_input(dicom)
        print("Launch")
        try:
            results = subprocess.run(
                [
                    "docker",
                    "run",
                    "--pull=always",
                    "--shm-size=2g",
                    "--gpus=all",
                    "--privileged",
                    "--rm",
                    "-v",
                    f"{self.input_dir}:/input/{self.uuid}",
                    "-v",
                    f"{self.temp_dir}/{self.uuid}:/output",
                    "-v",
                    "/data:/data",
                    "-v",
                    "/usr/share/zoneinfo/UTC:/etc/localtime:ro",
                    "--network",
                    "host",
                    "onsetlab/epinsight:1.0.2",
                    "nextflow",
                    "run",
                    "/epinsight/main.nf",
                    "--dicom",
                    f"/input/{self.uuid}",
                    "-profile",
                    "use_gpu,apptainer",
                    "--output_dir",
                    "/output/results",
                    "--fs_license",
                    "/assets/license.txt",
                    "--patient_id",
                    f"{patient_id}",
                    "--name",
                    f"{patient_name}"
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.output_paths = glob.glob(
                f"{self.temp_dir}/{self.uuid}/results/*__Bernarsconi/*.dcm")
            print(self.output_paths)
            self.output_paths.extend(glob.glob(
                f"{self.temp_dir}/{self.uuid}/results/*.dcm"))
            print(self.output_paths)
            for dcm in self.get_outputs():
                with open(dcm, "rb") as f:
                    content = f.read()
                    status = orthanc.RestApiPost("/instances", content)

        except subprocess.CalledProcessError as e:
            results = {
                "returncode": e.returncode,
                "stdout": e.stdout,
                "stderr": e.stderr,
            }
            print(e.stdout, e.stderr)
            orthanc.EmitAuditLog(
                "Epinsight",
                user_id,
                orthanc.ResourceType.STUDY,
                study_id,
                "SurgeryFlow - Failed",
                json.dumps(results),
            )
            return {}, e.returncode

        return status, results.returncode

    def get_outputs(self) -> str:
        return self.output_paths


def get_user_id(request):
    # decode the JWT keycloak token.  We don't verify the signature here because, it we get here,
    # it means that it has passed the token verification in the auth-plugin and we can trust the token.
    if "headers" in request and "token" in request["headers"]:

        _, payload, __ = request["headers"]["token"].split(".")
        payload += "=" * (-len(payload) % 4)

        decoded_keycloak_token = json.loads(base64.b64decode(payload).decode("utf-8"))
        return decoded_keycloak_token["preferred_username"], decoded_keycloak_token["email"], decoded_keycloak_token["name"]

    return None


def execute_epinsight(output, uri, **request):
    if request["method"] != "POST":
        output.SendMethodNotAllowed("POST")
    else:
        body = json.loads(request["body"])
        patient_name = str(body["patient-name"]).replace("^", " ").rstrip()
        patient_initials = ".".join(part[0].upper() for part in patient_name.split() if part) + "."
        patient_id = str(body["patient-id"])
        orthanc.LogInfo(f"EPINSIGHT: Load the original study {body['id']}")
        job = json.loads(orthanc.RestApiPost(f"/studies/{body['id']}/archive", json.dumps({"Asynchronous": True})))
        job_id = job["ID"]
        while True:
            job_status = json.loads(orthanc.RestApiGet(f"/jobs/{job_id}"))
            state = job_status["State"]
            if state == "Success":
                break
            elif state in ("Failure", "Cancelled"):
                raise RuntimeError(f"Archive job {job_id} ended with state: {state}")
            time.sleep(2)
        r = orthanc.RestApiGet(f"/jobs/{job_id}/archive")
        user_id, email, name = get_user_id(request)
        z = ZipFile(io.BytesIO(r))

        epinsight = EPINSIGHTRunner()
        orthanc.EmitAuditLog(
            epinsight.name,
            user_id,
            orthanc.ResourceType.STUDY,
            body["id"],
            f"{epinsight.name} - Start",
            None,
        )
        if email is not None:
            notification = JobNotification(email, f"ONSET-PACS - {epinsight.name} ({patient_initials})")
            notification.render_template(
                        name=name,
                        patient_name=patient_initials,
                        status="Submitted",
                        url=request["headers"]["referer"],
                        tool=epinsight.name)
            notification.send()
        try:
            _, err_code = epinsight.run(z, user_id, body["id"], patient_name, patient_id)
        finally:
            epinsight.clean_up()

        job_status = 1 if err_code == 0 else 2
        print(job_status)
        if notification is not None:
            if job_status == 1:
                notification.render_template(
                    name=name,
                    patient_name=patient_initials,
                    status="Completed",
                    url=request["headers"]["referer"],
                    status_color="green",
                    tool=epinsight.name,
                )
                orthanc.EmitAuditLog(
                    epinsight.name,
                    user_id,
                    orthanc.ResourceType.STUDY,
                    body["id"],
                    f"{epinsight.name} - Finished",
                    None
                )
            elif job_status == 2:
                notification.render_template(
                    name=name,
                    patient_name=patient_initials,
                    status="Failed",
                    url=request["headers"]["referer"],
                    status_color="red",
                    tool=epinsight.name,
                )
            notification.send()


orthanc.RegisterRestCallback("/epinsight-apply", execute_epinsight)
