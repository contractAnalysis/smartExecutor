
##  SmartExecutor ##

SmartExecutor is a guided symbolic execution tool for security analysis on EVM bytecode. It is designed to reduce the sequence explosion of symbolic execution to provide a scalable solution to symbolic execution while trying to maximize code coverage.  It has a dual-phase process. In Phase 1, it symbolically executes all possible function sequences within the given depth limit.

Phase 2 then targets the not-fully-covered functions based on instruction coverage. This is the phase where the guidance takes place. SmartExecutor can direct the execution flow by prioritizing the states more significant to the target functions and selecting the functions at states to be executed that are more likely to cover the targets. The state significance value calculation and the function selection are based on static data dependency analysis and runtime execution data like function coverage and target functions.


This is the [link](https://ieeexplore.ieee.org/document/10316942) to our conference paper: SmartExecutor: Coverage-Driven Symbolic Execution Guided by a Function Dependency Graph. The [documentation](https://page.d1xp6o5ammny8t.amplifyapp.com/) is available.



###  Run SmartExecutor through Docker: 

1, Pull the Docker image of SmartExecutor:
```bash
$ sudo docker pull 23278942/smartexecutor
```

2, Run SmartExecutor with a single Docker command. Replace a_host_directory with the path to your host directory containing the Solidity file, for example, Crowdsale.sol.
```bash
$ sudo docker run -it --rm -v a_host_directory:/home/smartExecutor/ --entrypoint semyth 3278942/smartexecutor:latest analyze ./Crowdsale.sol:Crowdsale
```
This command mounts the host directory to a directory inside the container and analyzes the contract Crowdsale defined in the Solidity file Crowdsale.sol.

To analyze the sample Solidity file provided with the Docker image, you can use the following command:
```bash
$ sudo docker run -it --rm --entrypoint semyth 3278942/smartexecutor:latest analyze /opt/smartExecutor/tests/testdata/solidity_files/Crowdsale.sol:Crowdsale 
```

3, Additional Options

To see more intermediate data, add the -v option followed by a value (3 or larger):
```bash
$ sudo docker run -it --rm --entrypoint semyth 3278942/smartexecutor:latest -v 3 analyze /opt/smartExecutor/tests/testdata/solidity_files/Crowdsale.sol:Crowdsale 
```

Click [here](./example_output/Crowdsale.sol_terminal_output.txt) to see the terminal output.

Click [here](./example_output/Crowdsale.sol_terminal_output_verbose.txt) to see the verbose intermediate results printed out in the terminal.

<!--
Example of running SmartExecutor inside the Docker container
```
# create and enter the Docker container that mounts a host directory to a directory inside the created container
sudo docker run -it --rm -v a_host_directory:/home/smartExecutor/ --entrypoint /bin/bash docker_image_id 

# call SmartExecutor to execute Contract Crowdsale defined in the Solidity file Crowdsale.sol
semyth analyze ./Crowdsale.sol:Crowdsale

# set option '-v' to 3 to show the verbose intermediate results
semyth -v 3 analyze ./Crowdsale.sol:Crowdsale 

```
-->


### Install solc-select and all versions of solc
```
pip install solc-select  # solc-select is a package to switch among different versions of solc (Solidity compiler)
solc-select install all  # install all possible versions of solc 
solc-select use 0.4.25   # example of using solc-select: set the version of solc to 0.4.25
```


### Run SmartExecutor in Pycharm IDE:

1, Create a project through Pycharm IDE by cloning https://github.com/contractAnalysis/smartExecutor.git.

2, Create a virtual environment and install dependencies.

3, Find semyth.py in the root directory and add the parameters. Take the example of Crowdsale.sol:
```
analyze
./tests/testdata/solidity_files/Crowdsale.sol:Crowdsale
```
4, Run semyth.py by right clicking it and select "Run semyth".


### Using SmartExecutor as a Command-Line Tool

Install SmartExecutor through pip:
```
pip install smartExecutorx
```

Run SmartExecutor:

```bash
$ semyth analyze <solidity-file>:<contract-name>
```
Replace <solidity-file> with the path to your Solidity file and <contract-name> with the name of the contract you want to analyze. 

<!--
Note that the usage of SmartExecutor is almost the same as Mythril except that you have to begin with **semyth** instead of **myth** and you need to include the option **-fdg**, which is used to signal that the scalable alternative is in active. When **-fdg** is not given, SmartExecutor runs the basic model, i.e., Mythril itself.

For this reason, here show some useful documents of Mythril:

- [Instructions for using Mythril](https://mythril-classic.readthedocs.io/en/master/)
- [Mythril's documentation](https://mythril-classic.readthedocs.io/en/develop/)
- [Vulnerability Remediation](https://swcregistry.io/)
-->
If you find this tool helpful, we would appreciate it if you could cite it. Here is the BibTex:
```text
@INPROCEEDINGS{10316942,
  author={Wei, Qiping and Sikder, Fadul and Feng, Huadong and Lei, Yu and Kacker, Raghu and Kuhn, Richard},
  booktitle={2023 5th Conference on Blockchain Research & Applications for Innovative Networks and Services (BRAINS)}, 
  title={SmartExecutor: Coverage-Driven Symbolic Execution Guided by a Function Dependency Graph}, 
  year={2023},
  volume={},
  number={},
  pages={1-8},
  keywords={Codes;Limiting;Smart contracts;Explosions;Ethereum smart contract;symbolic execution;vulnerability detection;sequence explosion;function dependency},
  doi={10.1109/BRAINS59668.2023.10316942}}

```
