Tutorial
======================


******************************************
Executing SmartExecutor on a contract
******************************************


We consider on contract Crowdsale.sol.

   .. code-block:: solidity

        pragma solidity ^0.4.25;
          contract Crowdsale {
          uint256 goal=100000*(10**18);
          uint256 phase=0;
          // 0: Active , 1: Success , 2: Refund
          uint256 raised;
          uint256 end;   address owner;
          mapping(address=>uint256) investments ;
          constructor() public{
            end=now+60 days ;
            owner=msg.sender ;
         }
          function invest() public payable{
            require(phase==0 && raised<goal);
            investments[msg.sender]+=msg.value ;
            raised+=msg.value ;
          }
          function setPhase(uint256 newPhase) public {
            require (
            (newPhase==1 && raised>=goal) ||
            (newPhase==2 && raised<goal && now>end));
            phase=newPhase ;
          }
          function setOwner(address newOwner) public {
            owner=newOwner ;
          }
          function withdraw() public {
            require(phase==1);
            owner.transfer(raised);
          }
          function refund() public {
            require(phase==2);
            msg.sender.transfer(investments[msg.sender]);
            investments[msg.sender]=0;
          }
        }

To analyze the contract using SmartExecutor, the following command can be used:

    .. code-block:: bash

        $ semyth analyze */Crowdsale.sol:Crowdsale

The output will show the vulnerabilities in the contract.

    .. code-block:: none

        ==== Integer Arithmetic Bugs ====
        SWC ID: 101
        Severity: High
        Contract: Crowdsale
        Function name: constructor
        PC address: 42
        Estimated Gas Usage: 21038 - 103767
        The arithmetic operator can overflow.
        It is possible to cause an integer overflow or underflow in the arithmetic operation.
        --------------------
        In file: ./tests/testdata/solidity_files/Crowdsale.sol:10

        now+60 days

        --------------------
        Initial State:

        Account: [CREATOR], balance: 0x0, nonce:0, storage:{}
        Account: [ATTACKER], balance: 0x0, nonce:0, storage:{}

        Transaction Sequence:

        Caller: [CREATOR], calldata: , decoded_data: , value: 0x0

        ==== Dependence on predictable environment variable ====
        SWC ID: 116
        Severity: Low
        Contract: Crowdsale
        Function name: setPhase(uint256)
        PC address: 415
        Estimated Gas Usage: 2729 - 2824
        A control flow decision is made based on The block.timestamp environment variable.
        The block.timestamp environment variable is used to determine a control flow decision. Note that the values of variables like coinbase, gaslimit, block number and timestamp are predictable and can be manipulated by a malicious miner. Also keep in mind that attackers know hashes of earlier blocks. Don't use any of those environment variables as sources of randomness and be aware that use of these variables introduces a certain level of trust into miners.
        --------------------
        In file: ./tests/testdata/solidity_files/Crowdsale.sol:19

        require (
            (newPhase==1 && raised>=goal) ||
            (newPhase==2 && raised<goal && now>end))

        --------------------
        Initial State:

        Account: [CREATOR], balance: 0x0, nonce:0, storage:{}
        Account: [ATTACKER], balance: 0x0, nonce:0, storage:{}

        Transaction Sequence:

        Caller: [CREATOR], calldata: , decoded_data: , value: 0x0
        Caller: [CREATOR], function: setPhase(uint256), txdata: 0x2cc826550000000000000000000000000000000000000000000000000000000000000002, decoded_data: (2,), value: 0x0




