Overview of SmartExecutor
=========================

SmartExecutor is a guided symbolic execution tool for security analysis on Ethereum smart contracts. It tries to cover more code while mitigating the issue of sequence explosion. the sequence explosion. We assume that the more code can be covered, the more vulnerabilities can be covered.


The symbolic execution process in SmartExecutor is a dual-phase process. In Phase 1, it symbolically executes all possible function sequences within the given depth limit. In this phase, the functions that are not fully covered are identified. The default value of the depth limit in Phase 1 is set to 1.

Phase 2 targets the not-fully-covered functions based on instruction coverage. This is the phase where the guidance takes place. SmartExecutor controls the execution flow by prioritizing the states more significant  to the target functions and selecting the functions at states to be executed that are more likely to cover the targets. The state significant value calculation and the function selection are based on data dependency analysis and runtime execution data like function coverage and target functions.


SmartExecutor is an open-source tool that can analyze Ethereum smart contracts and report potential security vulnerabilities in them. By analyzing the bytecode of a smart contract, it can identify and report on possible security vulnerabilities, such as reentrancy attacks, integer overflows, and other common smart contract vulnerabilities.
This tutorial explains how to use Mythril to analyze simple Solidity contracts for security vulnerabilities. A simple contract is one that does not have any imports.



This is the `link <https://ieeexplore.ieee.org/document/10316942>`_ to our conference paper: SmartExecutor: Coverage-Driven Symbolic Execution Guided by a Function Dependency Graph.


SmartExecutor is built on `Mythril <https://github.com/ConsenSys/mythril>`_, a symbolic-execution-based security analysis tool for EVM bytecode, which was
`introduced at HITBSecConf 2018 <https://github.com/b-mueller/smashing-smart-contracts/blob/master/smashing-smart-contracts-1of1.pdf>`_. It inherits everything from Mythril without changing except for the symbolic execution engine, which is under the control of SmartExecutor.

SmartExecutor detects a range of common vulnerabilities (not the issues in the business logic in contracts). In addition, like Mythril and other symbolic execution tools, SmartExecutor is generally unsound because it is not able to explore all possible state of a program.
