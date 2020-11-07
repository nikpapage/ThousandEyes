# AppDynamics & ThousandEyes Integration
AppDynamics extension to pull data from ThousandEyes tests and import them into AppDynamics using the APIs

###### Installation

1. Centos
    - Install and Configure the AppDynamics MachineAgent
    - Navigate to the machine agent directory under monitors
    - Clone the github repository
      ```
        git clone https://github.com/nikpapage/ThousandEyes.git
      ```
    - Navigate to the Extension's directory
      ```
        cd ThousandEyes
      ```
    - Provide the correct permissions to the executable files
      ```
        chmod 700 appdte.sh 
        chmod 700 appdte.py
      ```
    - Run the bash Script (Centos has a preinstall version of python and therefore there should'nt be any further changes)
      ```
        ./appdte.sh
      ```
    - The First time the code runs creates a script for the AppDynamics analytics schema creation. If needed run this adding the appropriate flags.
      ```
        chmod 700 createSchema.sh
        ./createSchema.sh -h 
        #Example: ./createSchema.sh -sc TE -ac global_account_hehg1h2b3jh5b4324n2nfs -k kkkkk-aaaaa-xxxxx-yyyyy -es "https://fra-ana-api.saas.appdynamics.com" -port          443
      ```
    - Change the frequency under monitor.xml
    - Restart the machine agent
    
2. Ubuntu
    - Install and Configure the AppDynamics MachineAgent
    - Navigate to the machine agent directory under monitors
    - Clone the github repository
      ```
        git clone https://github.com/nikpapage/ThousandEyes.git
      ```
    - Navigate to the Extension's directory
      ```
        cd ThousandEyes
      ```
    - Provide the correct permissions to the executable files
      ```
        chmod 700 appdte.sh 
        chmod 700 appdte.py
      ```
    - Install Python3 (The tested version of Ubuntu 18.04 does not have python installed)
      ```
        sudo apt install python3
      ```
    - Modify startup script to use the python3 installation
      ```
        vi appdte.sh
      ```
        change python to python3
    - Run the bash Script (Tes)
      ```
        sudo apt install python3
        ./appdte.sh
      ```
    - The First time the code runs creates a script for the AppDynamics analytics schema creation. If needed run this adding the appropriate flags.
      ```
        chmod 700 createSchema.sh
        ./createSchema.sh -h 
        #Example: ./createSchema.sh -sc TE -ac global_account_hehg1h2b3jh5b4324n2nfs -k kkkkk-aaaaa-xxxxx-yyyyy -es "https://fra-ana-api.saas.appdynamics.com" -port 443
      ```
    - Change the frequency under monitor.xml
    - Restart the machine agent
