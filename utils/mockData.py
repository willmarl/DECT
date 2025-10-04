import pandas as pd
from io import StringIO
import json
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
    "Foo_pdf": [
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
fakeJson2 = {
  "requirements": [
    {
      "id": "FR-1",
      "text": "The interface shall have two input fields, labeled \"From\" and \"To\""
    },
    {
      "id": "FR-2",
      "text": "The interface shall have a button labeled \"Calculate\""
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

fakeResponse2 = SimpleNamespace(
    id="chatcmpl-9hTzEXAMPLE123",
    object="chat.completion",
    choices=[
        SimpleNamespace(
            index=0,
            message=SimpleNamespace(
                role="assistant",
                content=json.dumps(fakeJson2)
            ),
            finish_reason="stop"
        )
    ]
)

fakeFinalOutput = {
  "document_id": "Urban_Scooter_Requirements_1.pdf",
  "test_suite": [
    {
      "fr_id": "FR-1",
      "test_cases": [
        {
          "title": "Verify the user can enter only Latin characters (2-25 characters)",
          "precondition": "User is on homepage, first name field is empty.",
          "steps": "Enter only Latin characters (2–25 chars).",
          "test_data": "Lula",
          "expected_result": "Latin characters are accepted.",
          "environment": "Test Environment",
          "actual_result": "",
          "status": "Not Executed",
          "jira_bug_link": ""
        },
        {
          "title": "Verify the user cannot enter numbers",
          "precondition": "User is on homepage, first name field is empty.",
          "steps": "Enter numbers.",
          "test_data": "123",
          "expected_result": "Numbers are not accepted.",
          "environment": "Test Environment",
          "actual_result": "",
          "status": "Not Executed",
          "jira_bug_link": ""
        }
      ]
    },
    {
      "fr_id": "FR-2",
      "test_cases": [
        {
          "title": "Verify the user can enter only Latin characters (2-25 characters) for last name",
          "precondition": "User is on homepage, last name field is empty.",
          "steps": "Enter valid last name.",
          "test_data": "Smith",
          "expected_result": "Last name accepted.",
          "environment": "Test Environment",
          "actual_result": "",
          "status": "Not Executed",
          "jira_bug_link": ""
        }
      ]
    }
  ]
}
