pragma solidity 0.6.5;
pragma experimental ABIEncoderV2;


interface ERC20 {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
    function balanceOf(address) external view returns (uint256);
}




struct TokenMetadata {
    address token;
    string name;
    string symbol;
    uint8 decimals;
}


struct Component {
    address token;    
    string tokenType; 
    uint256 rate;     
}



interface TokenAdapter {

    
    function getMetadata(address token) external view returns (TokenMetadata memory);

    
    function getComponents(address token) external view returns (Component[] memory);
}



interface SmartToken {
    function owner() external view returns (address);
    function totalSupply() external view returns (uint256);
}



interface BancorConverter {
    function connectorTokenCount() external view returns (uint256);
    function connectorTokens(uint256) external view returns (address);
}



interface ContractRegistry {
    function addressOf(bytes32) external view returns (address);
}



interface BancorFormula {
    function calculateLiquidateReturn(
        uint256,
        uint256,
        uint32,
        uint256
    )
        external
        view
        returns (uint256);
}



contract BancorTokenAdapter is TokenAdapter {

    address internal constant REGISTRY = 0x52Ae12ABe5D8BD778BD5397F99cA900624CfADD4;

    
    function getMetadata(address token) external view override returns (TokenMetadata memory) {
        return TokenMetadata({
            token: token,
            name: ERC20(token).name(),
            symbol: ERC20(token).symbol(),
            decimals: ERC20(token).decimals()
        });
    }

    
    function getComponents(address token) external view override returns (Component[] memory) {
        address formula = ContractRegistry(REGISTRY).addressOf("BancorFormula");
        uint256 totalSupply = SmartToken(token).totalSupply();
        address converter = SmartToken(token).owner();
        uint256 length = BancorConverter(converter).connectorTokenCount();

        Component[] memory underlyingTokens = new Component[](length);

        address underlyingToken;
        for (uint256 i = 0; i < length; i++) {
            underlyingToken = BancorConverter(converter).connectorTokens(i);

            underlyingTokens[i] = Component({
                token: underlyingToken,
                tokenType: "ERC20",
                rate: BancorFormula(formula).calculateLiquidateReturn(
                    totalSupply,
                    ERC20(underlyingToken).balanceOf(converter),
                    uint32(1000000),
                    uint256(1e18)
                )
            });
        }

        return underlyingTokens;
    }
}