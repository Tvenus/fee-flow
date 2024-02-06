import "methods/IFeeFlowController.spec";
import "helpers/erc20.spec";

using FeeFlowControllerHarness as feeFlowController;

// Reusable functions
function constructorAssumptions(env e) {
	uint initPriceStart = getInitPrice();
	uint minInitPriceStart = getMinInitPrice();
	uint ABS_MIN_INIT_PRICE = getABS_MIN_INIT_PRICE();
	uint ABS_MAX_INIT_PRICE = getABS_MAX_INIT_PRICE();
	uint MIN_PRICE_MULTIPLIER = getMIN_PRICE_MULTIPLIER();
	uint MAX_PRICE_MULTIPLIER = getMAX_PRICE_MULTIPLIER();

	//! if(initPrice < minInitPrice_) revert InitPriceBelowMin();
	require initPriceStart >= minInitPriceStart;
	
	//! if(initPrice > ABS_MAX_INIT_PRICE) revert InitPriceAboveMax();
	require initPriceStart <= ABS_MAX_INIT_PRICE;

	uint epochPeriodStart = getEpochPeriod();
	uint MIN_EPOCH_PERIOD = getMIN_EPOCH_PERIOD();
	
	//! if(epochPeriod_ < MIN_EPOCH_PERIOD) revert EpochPeriodBelowMin();
	require epochPeriodStart >= MIN_EPOCH_PERIOD;
	
	//! if(epochPeriod_ > MAX_EPOCH_PERIOD) revert EpochPeriodExceedsMax();
	uint MAX_EPOCH_PERIOD = getMAX_EPOCH_PERIOD();
	require epochPeriodStart <= MAX_EPOCH_PERIOD;

	uint priceMultiplierStart = getPriceMultiplier();
	
	//! if(priceMultiplier_ < MIN_PRICE_MULTIPLIER) revert PriceMultiplierBelowMin();
	require priceMultiplierStart >= MIN_PRICE_MULTIPLIER;

	// ! if(priceMultiplier_ > MAX_PRICE_MULTIPLIER) revert PriceMultiplierAboveMax();
	require priceMultiplierStart <= MAX_PRICE_MULTIPLIER;
	
	//! if(minInitPrice_ < ABS_MIN_INIT_PRICE) revert MinInitPriceBelowMin();
	require minInitPriceStart >= ABS_MIN_INIT_PRICE;

	//! if(minInitPrice_ > ABS_MAX_INIT_PRICE) revert MinInitPriceExceedsuint128();
	require minInitPriceStart <= ABS_MAX_INIT_PRICE;

	//! if(paymentReceiver_ == address(this)) revert PaymentReceiverIsThis();
	address paymentReceiver = getPaymentReceiver();
	require(paymentReceiver != feeFlowController);
}

function initialStateAssertions(env e) {
	uint initPrice = getInitPrice();
	uint minInitPrice = getMinInitPrice();
	uint epochPeriod = getEpochPeriod();
	uint priceMultiplier = getPriceMultiplier();
	uint startTime = getStartTime();
	uint MIN_EPOCH_PERIOD = getMIN_EPOCH_PERIOD();
	uint MIN_PRICE_MULTIPLIER = getMIN_PRICE_MULTIPLIER();
	uint ABS_MIN_INIT_PRICE = getABS_MIN_INIT_PRICE();
	uint ABS_MAX_INIT_PRICE = getABS_MAX_INIT_PRICE();

	assert initPrice >= minInitPrice, "initPrice >= minInitPrice";
	assert initPrice <= ABS_MAX_INIT_PRICE, "initPrice < ABS_MAX_INIT_PRICE";
	assert epochPeriod >= MIN_EPOCH_PERIOD, "epochPeriod >= MIN_EPOCH_PERIOD";
	assert priceMultiplier >= MIN_PRICE_MULTIPLIER, "priceMultiplier >= MIN_PRICE_MULTIPLIER";
	assert minInitPrice >= ABS_MIN_INIT_PRICE, "minInitPrice >= ABS_MIN_INIT_PRICE";
	assert minInitPrice <= ABS_MAX_INIT_PRICE, "minInitPrice <= ABS_MAX_INIT_PRICE";
	assert e.block.timestamp >= startTime, "e.block.timestamp >= startTime";
}

function requirementsForBuyExecution(env e, address[] assets, address assetsReceiver, uint256 deadline, uint256 maxPaymentTokenAmount) {
	reentrancyMock(); // this sets the lock to the correct initial value
	uint256 initPriceStart = getInitPrice();
	require(maxPaymentTokenAmount > initPriceStart);
	require(e.block.timestamp <= deadline);
	uint256 paymentAmount = getPrice(e);
	require(paymentAmount <= maxPaymentTokenAmount && paymentAmount > 0);
	require(e.msg.value == 0); // if we send ether the transaction will revert
	// we have enough allowance and we have enough balance
	uint256 allowance = feeFlowController.getPaymentTokenAllowance(e, e.msg.sender);
	uint256 balance = feeFlowController.getPaymentTokenBalanceOf(e, e.msg.sender);
	address receiver = feeFlowController.paymentReceiver();
	require(receiver != 0); // this is for us to cover the ERC20Basic implementation
	require(e.msg.sender != 0);

	uint256 receiverBalance = feeFlowController.getPaymentTokenBalanceOf(e, receiver);
	mathint receiverNewBalance = receiverBalance + paymentAmount;
	require(receiverNewBalance < max_uint256);
	require(balance >= paymentAmount && allowance >= balance);
	require(assets.length == 1); // making 1 transfer for simplicity

	address token = assets[0];
	require(assetsReceiver != 0); // make sure the receiver is not 0
	require(assetsReceiver != receiver); // make sure the receiver is not the payment receiver
	uint256 feeControllerTokenBalance = feeFlowController.getTokenBalanceOf(e, token, feeFlowController);
	uint256 assetReceiverTokenBalance = feeFlowController.getTokenBalanceOf(e, token, assetsReceiver);
	uint256 assetReceiverTokenBalanceAfter = require_uint256(feeControllerTokenBalance + assetReceiverTokenBalance);
}

persistent ghost bool reentrancy_happened {
    init_state axiom !reentrancy_happened;
}

hook CALL(uint g, address addr, uint value, uint argsOffset, uint argsLength, 
          uint retOffset, uint retLength) uint rc {
    if (addr == currentContract) {
        reentrancy_happened = reentrancy_happened 
                                || executingContract == currentContract;
    }
}


// Invariants
// NOTE: we are executing optimistic dispatches for the ERC20 tokens
invariant invariant_no_reentrant_calls() !reentrancy_happened;
invariant invariant_init_price_must_be_in_range() getInitPrice() >= getMinInitPrice() && getInitPrice() <= getABS_MAX_INIT_PRICE();
invariant invariant_price_must_be_below_max_init_price(env e) getPrice(e) <= getInitPrice();

// Rules
rule reachability(method f)
{
	env e;
	calldataarg args;
	feeFlowController.f(e,args);
	satisfy true, "a non-reverting path through this method was found";
}

rule check_initailStateAssertionsAfterBuy() {
	env e;
	constructorAssumptions(e);
	calldataarg args;
	buy(e, args);
	initialStateAssertions(e);
}

rule check_buyNeverRevertsUnexpectedly() {
	env e;
	constructorAssumptions(e);
	address[] assets; address assetsReceiver; uint256 deadline; uint256 maxPaymentTokenAmount;
	requirementsForBuyExecution(e, assets, assetsReceiver, deadline, maxPaymentTokenAmount);
	buy@withrevert(e, assets, assetsReceiver, deadline, maxPaymentTokenAmount);
	assert !lastReverted, "buy never reverts with arithmetic exceptions or internal solidity reverts";
}

rule check_buyNextInitPriceAtLeastBuyPriceTimesMultiplier() {
	env e;
	constructorAssumptions(e);
	calldataarg args;
	address[] assets; address assetsReceiver; uint256 deadline; uint256 maxPaymentTokenAmount;
	requirementsForBuyExecution(e, assets, assetsReceiver, deadline, maxPaymentTokenAmount);
	mathint paymentAmount = buy@withrevert(e, assets, assetsReceiver, deadline, maxPaymentTokenAmount);

	mathint priceMultiplier = getPriceMultiplier();
	mathint PRICE_MULTIPLIER_SCALE = getPRICE_MULTIPLIER_SCALE();
	mathint predictedInitPrice = paymentAmount * priceMultiplier / PRICE_MULTIPLIER_SCALE;

	mathint initPriceAfter = getInitPrice();
	mathint minInitPrice = getMinInitPrice();
	mathint absMaxInitPrice = getABS_MAX_INIT_PRICE();
	if (predictedInitPrice < minInitPrice) {
		assert initPriceAfter == minInitPrice, "initPrice == minInitPrice";
	} else {
		if(predictedInitPrice > absMaxInitPrice) { 
			assert initPriceAfter == absMaxInitPrice, "initPrice == ABS_MAX_INIT_PRICE";
		} else {
			assert initPriceAfter == predictedInitPrice, "initPrice == paymentAmount * priceMultiplier / PRICE_MULTIPLIER_SCALE";
		}
	}
}