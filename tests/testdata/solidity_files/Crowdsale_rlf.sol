pragma solidity >=0.4.25;
contract Crowdsale {
 uint256 raised ;
  uint256 closeTime;
   uint256 goal ;
    uint256 status ;
address owner ;
mapping ( address => uint256 ) deposits ;

constructor ( uint256 goalFund ) public {
closeTime = now + 30 days ;
owner = msg.sender ;
goal = goalFund ;
status = 0;
raised = 0;
}

function setStatus ( uint256 newStatus ) public {
require (( newStatus == 1 && raised >= goal ) ||
( newStatus == 2 && raised < goal && now >= closeTime ) ) ;
 status = newStatus ;
}

function setOwner ( address newOwner ) public {
// Debug : require (msg. sender == owner );
owner = newOwner ;
}

function invest () public payable {
require ( status == 0 && raised < goal ) ;
deposits [ msg.sender ] += msg.value ;
raised += msg.value ;
}

function withdraw () public {
require ( status == 1) ;
owner.transfer ( raised ) ;
}

function refund () public {
require ( status == 2) ;
// bug (); some operations with bug
msg. sender.transfer ( deposits [ msg.sender ]) ;
deposits [ msg.sender ] = 0;
}
}