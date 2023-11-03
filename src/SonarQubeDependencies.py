from sonarqube import SonarQubeClient

from datetime import datetime, timedelta
import os

import subprocess

import json



def sonarQubeLogin(url, username, password):
    '''
    Start a SonarQube session
    \n
    Parameters:
    \n
    String url: server URL
    \n
    String username: SonarQube username
    \n
    String password: SonarQube password
    \n
    Returns:
    \n
    SonarQubeClient sonar: SonarQube session
    '''
    sonar = SonarQubeClient(
        sonarqube_url=url, 
        username=username, 
        password=password
    )

    return sonar


def getExpirationDate(expirationDays):
    '''
    Get current date
    \n
    Returns:
    \n
    String date: current date
    '''
    date = (datetime.now() + timedelta(days=expirationDays)).strftime("%Y-%m-%d")
    return date


def doesProjectExist(sonar, projectKey):
    '''
    Search for a project in SonarQube
    \n
    Parameters:
    \n
    SonarQubeClient sonar: SonarQube session
    \n
    String projectKey: project key
    \n
    Returns:
    \n
    String projectKey: project key
    '''
    projects = sonar.projects.search_projects()
    exists = False
    i = 0

    while (i < len(projects['components']) and not exists):
        exists = projects['components'][i]['key'] == projectKey
        i += 1

    return exists 


def createNewProject(sonar, projectKey, projectName, projectVisibility, expirationDays):
    '''
    Create a new SonarQube project if it does not exist
    \n
    Parameters:
    \n
    SonarQubeClient sonar: SonarQube session
    \n
    String projectKey: project key
    \n
    String projectName: project name
    \n
    String projectVisibility: project visibility {public, private}
    \n
    Integer expirationDays: token expiration days
    '''
    success = False
    token = None

    if (not doesProjectExist(sonar, projectKey)):
        sonar.projects.create_project(
            project=projectKey, 
            name=projectName, 
            visibility=projectVisibility
        )
        success = True
        expirationDate = getExpirationDate(expirationDays)
        token = user_token = sonar.user_tokens.generate_user_token(
            name=f"Analyze \"{projectKey}\"",
            type="PROJECT_ANALYSIS_TOKEN",
            projectKey=projectKey,
            expirationDate=expirationDate)
        token = token['token']

    return success, token


def codeAnalysis(path, command):
    '''
    Analyze code with SonarQube
    \n
    Parameters:
    \n
    String path: project path
    \n
    String token: project token
    '''

    if (os.path.isdir(path)):
        # Change directory to project path, run sonar-scanner analysis and 
        # return to current directory
        currentDirectory = os.getcwd()
        os.chdir(path)
        process = subprocess.Popen(command, shell=True)
        process.wait()
        os.chdir(currentDirectory)
    else:
        print('Invalid path')


def extractIssues(sonar, regKey, metricKeys):
    '''
    Creates a dictionary with the issues of a project with the following format:
    \n
    {
        "ISSUE_1": [
            {
                "ruleID": "ruleID",
                "line": "line",
                "textRange": [
                    {
                        "startLine": 1,
                        "endLine": 1,
                        "startOffset": 0,
                        "endOffset": 0
                    }
                ]
            },
        ],
    }
    \n
    Parameters:
    \n
    SonarQubeClient sonar: SonarQube session
    \n
    String regKey: name of the project to be analyzed
    \n
    Returns:
    \n
    dict dictIssues: dictionary with the issues of the project
    '''
    issues = sonar.issues.search_issues(regKey)

    dictIssues = {}
    rulesDict = {}

    for issue in issues['issues']:
        if issue['type'][:-1] in metricKeys.upper():
            dictAux = {}

            # Extracts the rule ID, the rule description and the text range from 
            # each issue
            ruleID = issue['rule']
            rule = issue['message']
            textRange = issue['textRange']

            # Creates a dictionary with the mentioned information
            dictAux['ruleID'] = ruleID
            dictAux['line'] = rule
            dictAux['textRange'] = [textRange]

            # Checks if the key has already been created in the general dictionary
            # (we add the rule to its corresponding category) or creates the list
            # for the rules if it does not exist yet
            issueType = issue['type']
            
            if issueType in dictIssues:
                # Checks if the rule has already been added to the list of rules of
                # its category to avoid duplicating it and only add the text range
                # where it appears or, if the rule does not exist, adds it to the
                # dictionary and, from this moment on, consider its id to compare
                # with future rules
                if ruleID in rulesDict[issueType]:
                    ruleIdx = rulesDict[issueType].index(ruleID)
                    dictIssues[issueType][ruleIdx]['textRange'].append(textRange)
                else:
                    dictIssues[issueType].append(dictAux)
                    rulesDict[issueType].append(ruleID)
            else:
                dictIssues[issueType] = [dictAux]
                rulesDict[issueType] = [ruleID]
    
    return dictIssues


def extractHotspots(sonar, projectName):
    '''
    Creates a dictionary with the following format:
    \n
        {
            "ruleID": "ruleID",
            "line": "message",
            "textRange": "textRange"
        }
    \n
    Contains every hotspot found in the code files within the project.
    \n
    Parameters:
    \n
    SonarQubeClient sonar: client with the connection to the SonarQube server
    \n
    String projectName: name of the project to be analyzed
    \n
    Returns:
    \n
    list(String) fileNames: list of file names in the project
    \n
    list(list(dict)) hotspotDicts: list of hotspot dictionaries for each file
    '''
    # Extract every hotspot from every file in the project
    hotspots = sonar.hotspots.search_hotspots(projectKey=projectName)
    
    # Paralel lists of file names and their corresponding hotspot dictionaries
    fileNames = []
    hotspotDicts = []
    currentHotspotKeys = []

    for hs in hotspots['hotspots']:
        dictAux = {}
        dictAux['ruleID'] = hs['ruleKey']
        dictAux['line'] = hs['message']
        dictAux['textRange'] = [hs['textRange']]

        # Get the file name of the hotspot
        component = hs['component']
        ruleKey = hs['ruleKey']
        indexComp = -1

        # If we are exploring a new component, we update the data structures
        if component not in fileNames:
            fileNames.append(hs['component'])
            hotspotDicts.append([dictAux])
            currentHotspotKeys = [ruleKey]
            
        # If we are exploring a known component, we create a new hotspot 
        # dictionary iff the hotspot hasn't been found before. Otherwise, we
        # create a new textRange entry in the corresponding hotspot dictionary
        else:
            indexComp = fileNames.index(component)
            if ruleKey in currentHotspotKeys:
                indexKey = currentHotspotKeys.index(ruleKey)
                currentTxtRange = hotspotDicts[indexComp][indexKey]['textRange']
                currentTxtRange.append(hs['textRange'])
            else:
                hotspotDicts[indexComp].append(dictAux)
                currentHotspotKeys.append(ruleKey)
    
    return fileNames, hotspotDicts


def datasetAnalysis(sonar, projectName, branch, metricKeys='bugs,vulnerabilities,security_hotspots,code_smells'):
    '''
    Creates a dataset with the following format:
    \n
    {
        "data": [
            "id": "id of the register",
            "name": "name of the file",
            "code": "source code of the file",
            "language": "language of the source code",
            "measures": {
                "ISSUE_1": [
                    {
                        "ruleID": "ruleID",
                        "line": "line",
                        "textRange": [
                            {
                                "startLine": 1,
                                "endLine": 1,
                                "startOffset": 0,
                                "endOffset": 0
                            }
                        ]
                    },
                ],
            }
        ],
    }
    \n
    Parameters:
    \n
    SonarQubeClient sonar: client with the connection to the SonarQube server
    \n
    String projectName: name of the project to be analyzed
    \n
    String branch: name of the branch to be analyzed
    \n
    String metricKeys: list of metric keys to be analyzed. 
    Example: bugs,code_smells,vulnerabilities,security_hotspots
    \n
    Returns:
    \n
    dict dataset: dataset with the information mentioned above
    '''
    # Takes all the information from the project to be analyzed
    component = sonar.measures.get_component_tree_with_specified_measures(
        component=projectName,
        branch=branch,
        metricKeys=metricKeys
    )

    # Takes all the hotspots from the project to be analyzed
    fileNames, hotspotDicts = extractHotspots(sonar, projectName)

    listaDicts = []
    for reg in component['components']:
        if (reg['qualifier'] == 'FIL'):
            
            dictAux = {}

            # Project:[directory/]*file.extension
            regKey = reg['key'] 
            
            # Extracts the name of the file, the language and the source code
            name = reg['name']
            language = reg['language']
            source_code = sonar.sources.get_sources_raw(key=regKey)

            dictAux['id'] = 0
            dictAux['name'] = name
            dictAux['code'] = source_code
            dictAux['language'] = language

            # Extracts every issue listed in metricKeys
            dictIssues = extractIssues(sonar, regKey, metricKeys)
            
            if regKey in fileNames and 'security_hotspots' in metricKeys:
                currentHotspots = fileNames.index(regKey)
                dictIssues["SECURITY_HOTSPOT"] = hotspotDicts[currentHotspots]

            dictAux['measures'] = dictIssues

            # Computes the hash of each register using source code, the name
            # of the file and the number of found issues.
            hashNum = hash(source_code) + hash(name)

            for key in dictIssues.keys():
                hashNum += len(dictIssues[key])
            
            dictAux['id'] = hashNum
            listaDicts.append(dictAux)
    
    return {"data": listaDicts}