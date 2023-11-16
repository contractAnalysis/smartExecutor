/**
 *Submitted for verification at Etherscan.io on 2018-02-01
*/

pragma solidity ^0.4.25;


/**
 * @title SafeMath
 * @dev Math operations with safety checks that throw on error
 */
library SafeMath {
  function mul(uint256 a, uint256 b) internal pure returns (uint256) {
    if (a == 0) {
      return 0;
    }
    uint256 c = a * b;
    assert(c / a == b);
    return c;
  }

  function div(uint256 a, uint256 b) internal pure returns (uint256) {
    // assert(b > 0); // Solidity automatically throws when dividing by 0
    uint256 c = a / b;
    // assert(a == b * c + a % b); // There is no case in which this doesn't hold
    return c;
  }

  function sub(uint256 a, uint256 b) internal pure returns (uint256) {
    assert(b <= a);
    return a - b;
  }

  function add(uint256 a, uint256 b) internal pure returns (uint256) {
    uint256 c = a + b;
    assert(c >= a);
    return c;
  }
}


contract HoloToken_test_02{
  using SafeMath for uint256;
  bool public mintingFinished = false;  
  uint256 public totalSupply;  
  address public owner;
  mapping(address => uint256) public balances;
  
  address public destroyer;
  address public minter;

  modifier canMint() {
    require(!mintingFinished);
    _;
  }
 
  modifier onlyMinter() {
    require(msg.sender == minter);
    _;
  }

  modifier onlyDestroyer() {
     require(msg.sender == destroyer);
     _;
  }

  modifier onlyOwner() {
    require(msg.sender == owner);
    _;
  }

 constructor() public {
    owner = msg.sender;
  }  

  function setMinter(address _minter) external onlyOwner {
    minter = _minter;
  }

  function mint(address _to, uint256 _amount) external 
	onlyMinter canMint  returns (bool) {  
    totalSupply = totalSupply.add(_amount);
    balances[_to] = balances[_to].add(_amount);   
    return true;
  }
 
  function setDestroyer(address _destroyer) external onlyOwner {
    destroyer = _destroyer;
  }

  function burn(uint256 _amount) external onlyDestroyer {
    require(balances[destroyer] >=_amount && _amount > 0);   
    balances[destroyer] = balances[destroyer].sub(_amount);
    totalSupply = totalSupply.sub(_amount);   
  }
}



