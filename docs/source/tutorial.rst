Tutorial
======================

******************************************
Introduction
******************************************
SmartExecutor is a guided symbolic execution tool for security analysis on Ethereum smart contracts. It tries to cover more code while mitigating the issue of sequence explosion. the sequence explosion. We assume that the more code can be covered, the more vulnerabilities can be covered.


The symbolic execution process in SmartExecutor is a dual-phase process. In Phase 1, it symbolically executes all possible function sequences within the given depth limit. In this phase, the functions that are not fully covered are identified. The default value of the depth limit in Phase 1 is set to 1.

Phase 2 targets the not-fully-covered functions based on instruction coverage. This is the phase where the guidance takes place. SmartExecutor controls the execution flow by prioritizing the states more significant  to the target functions and selecting the functions at states to be executed that are more likely to cover the targets. The state significant value calculation and the function selection are based on data dependency analysis and runtime execution data like function coverage and target functions.


SmartExecutor is an open-source tool that can analyze Ethereum smart contracts and report potential security vulnerabilities in them. By analyzing the bytecode of a smart contract, it can identify and report on possible security vulnerabilities, such as reentrancy attacks, integer overflows, and other common smart contract vulnerabilities.
This tutorial explains how to use Mythril to analyze simple Solidity contracts for security vulnerabilities. A simple contract is one that does not have any imports. 


******************************************
Executing SmartExecutor on a contract
******************************************


We consider on contract Crowdsale.sol. this simple contract, ``Exceptions``, which has a number of functions, including ``assert1()``, ``assert2()``, and ``assert3()``, that contain Solidity ``assert()`` statements. We will use Mythril to analyze this contract and report any potential vulnerabilities.




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

The sample contract has several functions, some of which contain vulnerabilities. For instance, the ``assert1()`` function contains an assertion violation. To analyze the contract using Mythril, the following command can be used:

    .. code-block:: bash

        $ semyth analyze */Crowdsale.sol:Crowdsale

The output will show the vulnerabilities in the contract. In the case of the "Exceptions" contract, Mythril detected two instances of assertion violations.


    .. code-block:: none

        ==== Exception State ====
        SWC ID: 110
        Severity: Medium
        Contract: Exceptions
        Function name: assert1()
        PC address: 708
        Estimated Gas Usage: 207 - 492
        An assertion violation was triggered.
        It is possible to trigger an assertion violation. Note that Solidity assert() statements should only be used to check invariants. Review the transaction trace generated for this issue and either make sure your program logic is correct, or use require() instead of assert() if your goal is to constrain user inputs or enforce preconditions. Remember to validate inputs from both callers (for instance, via passed arguments) and callees (for instance, via return values).
        --------------------
        In file: solidity_examples/exceptions.sol:7

        assert(i == 0)

        --------------------
        Initial State:

        Account: [CREATOR], balance: 0x2, nonce:0, storage:{}
        Account: [ATTACKER], balance: 0x0, nonce:0, storage:{}

        Transaction Sequence:

        Caller: [CREATOR], calldata: , value: 0x0
        Caller: [ATTACKER], function: assert1(), txdata: 0xb34c3610, value: 0x0

        ==== Exception State ====
        SWC ID: 110
        Severity: Medium
        Contract: Exceptions
        Function name: assert3(uint256)
        PC address: 708
        Estimated Gas Usage: 482 - 767
        An assertion violation was triggered.
        It is possible to trigger an assertion violation. Note that Solidity assert() statements should only be used to check invariants. Review the transaction trace generated for this issue and either make sure your program logic is correct, or use require() instead of assert() if your goal is to constrain user inputs or enforce preconditions. Remember to validate inputs from both callers (for instance, via passed arguments) and callees (for instance, via return values).
        --------------------
        In file: solidity_examples/exceptions.sol:20

        assert(input != 23)

        --------------------
        Initial State:

        Account: [CREATOR], balance: 0x40207f9b0, nonce:0, storage:{}
        Account: [ATTACKER], balance: 0x0, nonce:0, storage:{}

        Transaction Sequence:

        Caller: [CREATOR], calldata: , value: 0x0
        Caller: [SOMEGUY], function: assert3(uint256), txdata: 0x546455b50000000000000000000000000000000000000000000000000000000000000017, value: 0x0


One of the functions, ``assert5(uint256)``, should also have an assertion failure, but it is not detected because Mythril's default configuration is to run three transactions. 
To detect this vulnerability, the transaction count can be increased to four using the ``-t`` option, as shown below:

.. code-block:: bash

    $ myth analyze <file_path> -t 4

This gives the following execution output:


    .. code-block:: none

