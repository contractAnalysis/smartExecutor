Installation and Setup
======================


**************
PyPI on Ubuntu
**************

.. code-block:: bash

   # Update
   sudo apt update

   # Install solc
   sudo apt install software-properties-common
   sudo add-apt-repository ppa:ethereum/ethereum
   sudo apt install solc

   # Install libssl-dev, python3-dev, and python3-pip
   sudo apt install libssl-dev python3-dev python3-pip

   # Install smartExecutorx
   pip3 install smartExecutorx
   semyth version


******
Docker
******


1, Pull the Docker image of SmartExecutor:

    .. code-block:: bash

        $ sudo docker pull 23278942/smartexecutor


2, Run SmartExecutor with a single Docker command. Replace a_host_directory with the path to your host directory containing the Solidity file, for example, Crowdsale.sol.

    .. code-block:: bash

        $ sudo docker run -it --rm -v a_host_directory:/home/smartExecutor/ image_id analyze ./Crowdsale.sol:Crowdsale

This command mounts the host directory to a directory inside the container and analyzes the contract Crowdsale defined in the Solidity file Crowdsale.sol.

To analyze the sample Solidity file provided with the Docker image, you can use the following command:

    .. code-block:: bash

        $ sudo docker run -it --rm image_id analyze /opt/smartExecutor/tests/testdata/solidity_files/Crowdsale.sol:Crowdsale


3, Additional Options

To see more intermediate data, add the -v option followed by a value (3 or larger):

    .. code-block:: bash

        $ sudo docker run -it --rm image_id -v 3 analyze /opt/smartExecutor/tests/testdata/solidity_files/Crowdsale.sol:Crowdsale



