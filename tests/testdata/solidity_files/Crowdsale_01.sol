// SPDX-License-Identifier: MIT
pragma solidity ^0.4.25;

contract Crowdsale {
    // State Variables
    uint256 public goal = 100000 * (10**18);

    uint256 public raised;
    uint256 public end;
    address public owner;
    mapping(address => uint256) public investments;
    uint256 public phase = 0; // 0: Active , 1: Success , 2: Refund

    // Constructor
    constructor() public {
        end = now + 60 days;
        owner = msg.sender;
    }

    // Modifiers
    modifier onlyInPhase(uint256 requiredPhase) {
        require(phase == requiredPhase);
        _;
    }

    // Functions
    function invest() public payable onlyInPhase(0) {
        require(raised < goal);
        investments[msg.sender] += msg.value;
        raised += msg.value;
    }

    function setPhase(uint256 newPhase) public {
        require(
            (newPhase == 1 && raised >= goal) ||
            (newPhase == 2 && raised < goal && now > end)
        );
        phase = newPhase;
    }

    function setOwner(address newOwner) public {
        owner = newOwner;
    }

    function withdraw() public onlyInPhase(1) {
        owner.transfer(raised);
    }

    function refund() public onlyInPhase(2) {
        msg.sender.transfer(investments[msg.sender]);
        investments[msg.sender] = 0;
    }
}
