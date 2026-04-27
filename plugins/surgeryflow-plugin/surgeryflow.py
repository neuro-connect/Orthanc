##
## Load the deep learning model
##
import io
import os
import sys
import json
import shutil
import tempfile
import uuid
from zipfile import ZipFile
import glob
import subprocess
import base64

import orthanc
from notifications import JobNotification

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

sys.path.append(os.path.join(SCRIPT_DIR, ".."))


class SURGERYFLOWTRunner:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.input_dir = None
        self.mni_template_path = None
        self.uuid = None
        self.output_paths = None
        self.name = "SurgeryFlow"

    def _create_input(self, dicom: ZipFile):
        self.uuid = uuid.uuid4().hex
        self.input_dir = os.path.join(self.temp_dir, self.uuid, "input")
        dicom.extractall(self.input_dir)

    def clean_up(self):
        if self.uuid:
            shutil.rmtree(os.path.join(self.temp_dir, self.uuid), ignore_errors=True)

    def run(self, dicom: ZipFile, user_id: str, study_id: str):
        self._create_input(dicom)

        try:
            results = subprocess.run(
                [
                    "docker",
                    "run",
                    "--pull=always",
                    "--shm-size=2g",
                    "--gpus=all",
                    "--rm",
                    "-v",
                    f"{self.input_dir}:/input/{self.uuid}",
                    "-v",
                    f"{self.temp_dir}/{self.uuid}:/output",
                    "onsetlab/surgeryflow:chum_2.0.1",
                    "nextflow",
                    "run",
                    "/SurgeryFlow/main.nf",
                    "--input",
                    f"/input/{self.uuid}",
                    "-profile",
                    "standard,use_gpu",
                    "--out_dicom_dir",
                    "/output/results",
                    "--bundles",
                    '"AF_L" "AF_R" "CC_Fr_1" "CC_Fr_2" "CC_Oc" "CC_Pa" "CC_Pr_Po" "CC_Te" "CG_L" "CG_R" "FAT_L" "FAT_R" "FPT_L" "FPT_R" "FX_L" "FX_R" "ICP_L" "ICP_R" "IFOF_L" "IFOF_R" "ILF_L" "ILF_R" "MCP" "MdLF_L" "MdLF_R" "OR_ML_L" "OR_ML_R" "POPT_L" "POPT_R" "PYT_L" "PYT_R" "SCP_L" "SCP_R" "SLF_L" "SLF_R" "UF_L" "UF_R"',
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.output_paths = glob.glob(
                f"{self.temp_dir}/{self.uuid}/results/*__SurgeryFlow/*/*.dcm")
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
            orthanc.EmitAuditLog(
                "SurgeryFlow",
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


def execute_surgeryflow(output, uri, **request):
    if request["method"] != "POST":
        output.SendMethodNotAllowed("POST")
    else:
        body = json.loads(request["body"])
        patient_name = str(body["patient-name"]).replace("^", " ").rstrip()
        orthanc.LogInfo(f"SURGERYFLOW: Load the original study {body['id']}")
        r = orthanc.RestApiGet(f"/studies/{body['id']}/archive")
        user_id, email, name = get_user_id(request)
        z = ZipFile(io.BytesIO(r))

        surgeryflow = SURGERYFLOWTRunner()
        orthanc.EmitAuditLog(
            surgeryflow.name,
            user_id,
            orthanc.ResourceType.STUDY,
            body["id"],
            f"{surgeryflow.name} - Start",
            None,
        )
        if email is not None:
            notification = JobNotification(email, f"ONSET-PACS - {surgeryflow.name} ({patient_name})")
            notification.render_template(
                        name=name,
                        patient_name=patient_name,
                        status="Submitted",
                        url=request["headers"]["referer"],
                        tool=surgeryflow.name)
            notification.send()
        status, err_code = surgeryflow.run(z, user_id, body["id"])
        
        job_status = 1 if err_code == 0 else 2
        print(job_status)
        if job_status == 1:
            notification.render_template(
                name=name,
                patient_name=patient_name,
                status="Completed",
                url=request["headers"]["referer"],
                status_color="green",
                tool=surgeryflow.name,
            )
            orthanc.EmitAuditLog(
                surgeryflow.name,
                user_id,
                orthanc.ResourceType.STUDY,
                body["id"],
                f"{surgeryflow.name} - Finished",
                None
            )
        elif job_status == 2:
            notification.render_template(
                name=name,
                patient_name=patient_name,
                status="Failed",
                url=request["headers"]["referer"],
                status_color="red",
                tool=surgeryflow.name,
            )
        notification.send()


orthanc.RegisterRestCallback("/surgeryflow-apply", execute_surgeryflow)
