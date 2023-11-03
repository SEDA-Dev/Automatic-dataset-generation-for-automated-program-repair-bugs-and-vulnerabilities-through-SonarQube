import SonarQubeDependencies as sqd

###########################    SESION INIT    ##################################

# The url, username and password must be changed to the ones of the 
# server where the SonarQube instance is running
url = 'http://localhost:9000'
username = 'admin'
password = 'zbu3WAQX5dtT5Tk'

# SonarQube session init
sonar = sqd.sonarQubeLogin(url, username, password)


##########################    PARAMETER INIT    ################################

branch = 'main' # Branch of each project to analyze

# Reads the file where each projectKey, projectName and token are stored
tokensPath = "AnalysisProjects.json"
f = open(tokensPath, "r")
analysisProjects = sqd.json.load(f)

finalJson = {"data": []}


##############################    MAIN    ######################################

# Reads each project created with the other script
for register in analysisProjects["data"]:

    projectKey = register["projectKey"]
    projectName = register["projectName"]
    token = register["token"]

    tmpDict = sqd.datasetAnalysis(sonar, projectName, branch)
    
    for reg in tmpDict["data"]:
        finalJson["data"].append(reg)

print(sqd.json.dumps(finalJson, indent=4))
f = open("AnalysisReport.json", "w")
f.write(sqd.json.dumps(finalJson, indent=4))
f.close()