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

scan = True     # True to run a project scan, False to skip it
success = False # Remains False if the project already exists

# Path where sonar-scanner is located
sonarscanner_path = "C:\\sonarscanner\\bin" 

# Path where the project to analyze is located
path = "C:\\sonarscanner\\bin\\SoftwareX" 
expirationDays = 30    # Token expiration days

# Stores the token of the new project to print it, remains None if the project
# already exists
token = None    

# It is recommended that projectKeys = projectNames
projectKeys = ['Scan07']     # Project ID
projectNames = ['Scan07']    # Project name

# Creates a file to store each projectKey, projectName and token
finalJson = {"data": []}
tokensPath = "AnalysisProjects.json"
f = open(tokensPath, "w")


##############################    MAIN    ######################################

if (len(projectKeys) != len(projectNames)):
    print("The number of projectKeys and projectNames must be the same")
    exit(1)

else:
    for i in range(len(projectKeys)):

        projectKey = projectKeys[i]
        projectName = projectNames[i]

        # Create a new project if it does not exist
        if token == None and scan:
            # Creates the project and stores the token and the 
            # success of the operation
            success, token = sqd.createNewProject(sonar, 
                                                projectKey,
                                                projectName,
                                                'private', 
                                                expirationDays)
            
            message = "Success" if success else "Failure" 

            tmpDict = {"id": i,
                    "projectKey": projectKey, 
                    "projectName": projectName, 
                    "token": token,
                    "message": message}

            # Prints the result to follow the process 
            print(sqd.json.dumps(tmpDict, indent=4))  
            print("\n\n")  
            finalJson["data"].append(tmpDict)

            if success:
                command = f'cd {sonarscanner_path} && \
                            sonar-scanner -D"sonar.projectKey={projectKey}" \
                            -D"sonar.projectName={projectName}" \
                            -D"sonar.sources={path}" -D"sonar.host.url={url}" \
                            -D"sonar.login={token}'
                try:
                    # Checks if the command can be executed, if not, 
                    # the program ends. Otherwise, the analysis is executed
                    sqd.subprocess.check_call(command, shell=True)
                    sqd.codeAnalysis(path, command)

                except:
                    print("The command is not valid")
                    exit(1) 
            
            token = None


    # The JSON is written to the file and the file is closed
    f.write(sqd.json.dumps(finalJson, indent=4))
    f.close()