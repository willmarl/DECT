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