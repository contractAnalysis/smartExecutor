SmartExecutor
========================

SmartExecutor is a symbolic execution tool for security analysis on Ethereum smart contracts. It enables guidance to the symbolic exection process to reduce the problem of sequence explosion while trying to maximize the code coverage (or instruction coverage).


This is the `link <https://ieeexplore.ieee.org/document/10316942>`_ to our conference paper: SmartExecutor: Coverage-Driven Symbolic Execution Guided by a Function Dependency Graph.


SmartExecutor is built on `Mythril <https://github.com/ConsenSys/mythril>`_, a symbolic-execution-based security analysis tool for EVM bytecode, which was
`introduced at HITBSecConf 2018 <https://github.com/b-mueller/smashing-smart-contracts/blob/master/smashing-smart-contracts-1of1.pdf>`_. It inherits everything from Mythril without changing except for the symbolic execution engine, which is under the control of SmartExecutor.

SmartExecutor detects a range of common vulnerabilities (not the issues in the business logic in contracts). In addition, like Mythril and other symbolic execution tools, SmartExecutor is generally unsound because it is not able to explore all possible state of a program.
