====================
Command Line Options
====================

These are the options that can be configured.


.. option:: -p1dl , --phase1-depth-limit

    Set the depth limit for Phase 1.

    Default: 1


.. option:: --execution-times-limit

    Set the times a function can be assigned to execute in Phase 2.

    Default: 5


.. option:: --seq-len-limit

    Set the maximum depth length to be considered.

    Default: 4



.. option:: -fct <%>, --function-coverage-threshold <%>

    Set the coverage threshold for functions to be considered covered.

    Default: 89%


.. option:: --consider-all-reads

    Consider all the state variables read in a function.

    0: does not consider.

    1: consider.

    Default: 0


.. option:: --optimization

    About collecting the addresses used in contracts to expand the values of msg.sender.

    0: does not collect.

    1: collect.

    Default: 1



.. option:: --create-timeout <seconds>

    Set the amount of seconds to spend on the initial contract creation.

    Default: 10 seconds


.. option:: --preprocess-timeout <second>

    Set the time for the special transaction to collect function-level data.

    Default: 100 seconds


.. option:: --execution-timeout <second>

    Set the amount of seconds to spend on symbolic execution.

    Default: 86400 seconds


.. option:: --solver-timeout <milli seconds>

    Set the maximum amount of time(in milli seconds) the solver spends for queries from analysis modules.

    Default: 10000 milli seconds


.. option:: -fss , --function-search-strategy

    Select the strategy to select states (world states), at which functions will be assigned to execute. The strategies include BFS, DFS, and mine.

    Default: mine


.. option:: -seq , --sequences

    Provide the sequences to be executed. When the -fss is set to seq, this option should be set.

    Default: None


.. option:: -p , --print-function-coverage

    Print function coverage.

    0: does not print

    1: print

    Default: 1



.. option:: --random-baseline

    Randomly select functions to be executed at a state based on BFS. The percent of functions to be executed is given after this option. The value is a value from [1,2,3,4,5,6,7,8,10].

    1: 10% functions defined in a contract.

    5: 50% ...

    Default: None


.. option:: --no-guidance

    Flag to allow guidance in the symbolic execution process. When it appears, it means the basic symbolic execution without any guidance.

    Default: False

.. option:: -t, --transaction-count

    Set the maximum number of transactions issued by laser, which is effective when --no-guidance option is enabled.

    Default: 2

