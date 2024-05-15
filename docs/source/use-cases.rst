=========
Use Cases
=========


Execute Contract Crowdsale
****************************************************************************

    $ semyth analyze */Crowdsale.sol:Crowdsale



Execute Contract Crowdsale with more intermediate data
****************************************************************************

Use option :option:`-v`::

    $ semyth -v3 analyze */Crowdsale.sol:Crowdsale


Execute Contract Crowdsale with the depth limit of Phase 1 is 2
****************************************************************************

Use option :option:`-p1dl`::

    $ semyth analyze */Crowdsale.sol:Crowdsale -p1dl 2





Execute a list of given function sequences on contract Crowdsale
****************************************************************************

Use option :option:`-fss` and :option:`--sequences`::

    $ semyth analyze */Crowdsale.sol:Crowdsale -fss seq --sequences "[['invest()', 'setPhase(uint256)', 'withdraw()'],['setPhase(uint256)', 'refund()']]"


Execute contract Crowdsale with functions randomly selected to be executed at states.
*************************************************************************************

Use option :option:`--random-baseline`::

    $ semyth analyze */Crowdsale.sol:Crowdsale --random-baseline 7




Execute all possible sequences on contract Crowdsale with the depth limit set to 2
****************************************************************************

Use option :option:`--no-guidance`::

    $ semyth analyze */Crowdsale.sol:Crowdsale --no-guidance


Execute all possible sequences on contract Crowdsale with a depth limit of 3.
****************************************************************************

Use option :option:`--no-guidance` and option :option:`-t`::

    $ semyth analyze */Crowdsale.sol:Crowdsale --no-guidance -t 3
