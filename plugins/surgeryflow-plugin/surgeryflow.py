##
## Load the deep learning model
##
import io
import os
import sys
import json
import tempfile
import uuid
from zipfile import ZipFile
import glob
import subprocess
import base64

import orthanc

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

sys.path.append(os.path.join(SCRIPT_DIR, ".."))


class SURGERYFLOWTRunner:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.input_dir = None
        self.mni_template_path = None
        self.uuid = None

    def _create_input(self, dicom: ZipFile):
        self.uuid = uuid.uuid4().hex
        self.input_dir = os.path.join(self.temp_dir, self.uuid, "input")
        dicom.extractall(self.input_dir)

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
                    "onsetlab/surgeryflow:chum_latest",
                    "nextflow",
                    "run",
                    "/SurgeryFlow/main.nf",
                    "--input",
                    f"/input/{self.uuid}",
                    "-profile",
                    "standard,use_gpu",
                    "--output_dir",
                    "/output/results",
                    "--bundles",
                    '"OR_ML_L" "OR_ML_R" "PYT_L" "PYT_R" "SLF_L" "SLF_R" "AF_L" "AF_R" "IFOF_L" "IFOF_R" "ILF_L" "ILF_R" "FAT_L" "FAT_R"',
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

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
            raise

        self.output_paths = glob.glob(
            f"{self.temp_dir}/{self.uuid}/results/*__SurgeryFlow/*.dcm"
        )

    def get_outputs(self) -> str:
        return self.output_paths


def get_user_id(request):
    # decode the JWT keycloak token.  We don't verify the signature here because, it we get here,
    # it means that it has passed the token verification in the auth-plugin and we can trust the token.
    if "headers" in request and "token" in request["headers"]:

        _, payload, __ = request["headers"]["token"].split(".")
        payload += "=" * (-len(payload) % 4)

        decoded_keycloak_token = json.loads(base64.b64decode(payload).decode("utf-8"))
        return decoded_keycloak_token["preferred_username"]

    return None


def execute_surgeryflow(output, uri, **request):
    if request["method"] != "POST":
        output.SendMethodNotAllowed("POST")
    else:
        body = json.loads(request["body"])
        orthanc.LogInfo(f"SURGERYFLOW: Load the original study {body['id']}")
        r = orthanc.RestApiGet(f"/studies/{body['id']}/archive")
        user_id = get_user_id(request)
        z = ZipFile(io.BytesIO(r))

        surgeryflow = SURGERYFLOWTRunner()
        orthanc.EmitAuditLog(
            "SurgeryFlow",
            user_id,
            orthanc.ResourceType.STUDY,
            body["id"],
            "SurgeryFlow - Start",
            None,
        )
        surgeryflow.run(z, user_id, body["id"])

        for dcm in surgeryflow.get_outputs():
            with open(dcm, "rb") as f:
                content = f.read()
                status = orthanc.RestApiPost("/instances", content)
        orthanc.EmitAuditLog(
            "SurgeryFlow",
            user_id,
            orthanc.ResourceType.STUDY,
            body["id"],
            "SurgeryFlow - Finished",
            json.dumps(status),
        )
        output.AnswerBuffer(status, "application/json")


orthanc.RegisterRestCallback("/surgeryflow-apply", execute_surgeryflow)
