import pandas as pd
from io import StringIO

def gen_csv():
    dummyData = """
    "FR ID","Test Case","Precondition","Steps","Test Data","Expected Result","Environment","Actual Result","Test Status (Pass / Fail)","Jira Bug Link"
    "FR-1","Verify the user can enter only Latin characters (2-25 characters)","The user is on the homepage. The first name field is empty.","Enter only Latin characters (2-25 characters)","**Lula**","Latin characters are accepted.","Test Environment","Latin characters are accepted.","",""
    "FR-1","Verify the user cannot enter numbers","The user is on the homepage. The first name field is empty.","Enter numbers","**123**","Numbers are not accepted.","Test Environment","Numbers are not accepted.","",""
    "FR-1","Verify the user cannot enter special characters","The user is on the homepage. The first name field is empty.","Enter special characters","**!@#**","Special characters are not accepted.","Test Environment","Special characters are not accepted.","",""
    "Fr-1","Verify the user cannot enter non-Latin characters","The user is on the homepage. The first name field is empty.","Enter non-Latin characters","**愛している**","Non-Latin characters are not accepted.","Test Environment","Non-Latin characters are not accepted.","",""
    """
    df = pd.read_csv(StringIO(dummyData))
    return df

dummyData = gen_csv()

fakeJson = {
    "FRs": [
        {
            "id": "FR-001",
            "description": "The system shall allow users to create an account using their email address and a password.",
            "priority": "High",
            "acceptance_criteria": [
                "Users can register with a valid email and password.",
                "An account confirmation email is sent upon registration."
            ]
        },
        {
            "id": "FR-002",
            "description": "The system shall allow users to log in using their registered email and password.",
            "priority": "High",
            "acceptance_criteria": [
                "Users can log in with correct credentials.",
                "An error message is displayed for incorrect credentials."
            ]
        }
    ]
}

from types import SimpleNamespace
fakeResponse = SimpleNamespace(
    id="chatcmpl-9hTzEXAMPLE123",
    object="chat.completion",
    choices=[
        SimpleNamespace(
            index=0,
            message=SimpleNamespace(
                role="assistant",
                content='{\n  "user": "alex",\n  "age": 23\n}'
            ),
            finish_reason="stop"
        )
    ]
)