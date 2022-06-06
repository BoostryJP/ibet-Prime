"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
from typing import Tuple


def error_code_msg(code_str: str) -> Tuple[int, str]:
    """Retrieve contract error message from error code.

    :param code_str: error code thrown by contract
    :return: [error_code, error_message]
    """
    if not code_str.isdigit():
        # If contract doesn't throw error code,
        # consider the raw message as an error log.
        return 999999, code_str

    code = int(code_str)
    return code, {
        # TokenList (10XXXX)
        100001: "The address has already been registered.",
        100002: "Message sender must be the token owner.",
        100101: "The address has not been registered.",
        100102: "Message sender must be the token owner.",
        # IbetShare (11XXXX)
        110001:	"Lock address is invalid.",
        110002: "Lock amount is greater than message sender balance.",
        110101: "Unlock address is invalid.",
        110102: "Unlock amount is greater than locked amount.",
        110201: "The token isn't transferable.",
        110202: "Destination address check is failed.",
        110301: "Destination address isn't tradable exchange.",
        110401: "Message sender balance is insufficient.",
        110402: "The token isn't transferable.",
        110501: "Transferring of this token requires approval.",
        110502: "Length of To and of Value aren't matched.",
        110503: "Transfer amount is greater than from address balance.",
        110504: "The token isn't transferable.",
        110601: "Transfer amount is greater than from address balance.",
        110701: "Apply for transfer is invalid.",
        110702: "Destination address check is failed.",
        110801: "Canceling application for transfer is invalid.",
        110802: "Application is invalid.",
        110901: "Token isn't transferable.",
        110902: "Application is invalid.",
        111001: "Offering is stopped.",
        111002: "Personal information of message sender isn't registered to token owner.",
        111101: "Redeem amount is less than locked address balance.",
        111102: "Redeem amount is less than target address balance.",
        # IbetStraightBond (12XXXX)
        120001: "Lock address is invalid.",
        120002: "Lock amount is greater than message sender balance.",
        120101: "Unlock address is invalid.",
        120102: "Unlock amount is greater than locked amount.",
        120201: "The token isn't transferable.",
        120202: "Destination address check is failed.",
        120301: "Destination address isn't tradable exchange.",
        120401: "Message sender balance is insufficient.",
        120402: "The token isn't transferable.",
        120501: "Length of To and of Value aren't matched.",
        120502: "Transfer amount is greater than from address balance.",
        120503: "The token isn't transferable.",
        120601: "Transfer amount is greater than from address balance.",
        120701: "Apply for transfer is invalid.",
        120702: "Destination address check is failed.",
        120801: "Canceling application for transfer is invalid.",
        120802: "Application is invalid.",
        120901: "Token isn't transferable.",
        120902: "Application is invalid.",
        121001: "Offering is stopped.",
        121002: "Personal information of message sender isn't registered to token owner.",
        121101: "Redeem amount is less than locked address balance.",
        121102: "Redeem amount is less than target address balance.",
        # IbetCoupon (13XXXX)
        130001: "Destination address isn't tradable exchange.",
        130101: "Message sender balance is insufficient.",
        130102: "The token isn't transferable.",
        130201: "Length of To and of Value aren't matched.",
        130202: "Transfer amount is greater than from address balance.",
        130203: "The token isn't transferable.",
        130301: "Transfer amount is greater than from address balance.",
        130401: "Message sender balance is insufficient.",
        130501: "Offering is stopped.",
        130502: "Personal information of message sender isn't registered to token owner.",
        # IbetMembership (14XXXX)
        140001: "Destination address isn't tradable exchange.",
        140101: "Message sender balance is insufficient.",
        140102: "The token isn't transferable.",
        140201: "Length of To and of Value aren't matched.",
        140202: "Transfer amount is greater than from address balance.",
        140203: "The token isn't transferable.",
        140301: "Transfer amount is greater than from address balance.",
        140401: "Offering is stopped.",
        140402: "Personal information of message sender isn't registered to token owner.",
        # IbetStandardToken (15XXXX)
        150001: "Destination address isn't tradable exchange.",
        150101: "Message sender balance is insufficient.",
        150201: "Length of To and of Value aren't matched.",
        150202: "Transfer amount is greater than from address balance.",
        150301: "Transfer amount is greater than from address balance.",
        # ExchangeStorage (20XXXX)
        200001: "Message sender(exchange contract) isn't latest version.",
        # IbetExchange (21XXXX)
        210001: "Create order condition is invalid.",
        210101: "Cancel order ID is invalid.",
        210102: "Amount of target order is remaining.",
        210103: "Order has already been canceled.",
        210104: "Message sender is not the order owner.",
        210201: "Cancel order ID is invalid.",
        210202: "Amount of target order is remaining.",
        210203: "Order has already been canceled.",
        210204: "Message sender is not the order agent.",
        210301: "Target order ID is invalid.",
        210302: "Execute order condition is invalid.",
        210401: "Target order ID is invalid.",
        210402: "Target agreement ID is invalid.",
        210403: "Agreement condition is invalid.",
        210501: "Target order ID is invalid.",
        210502: "Target agreement ID is invalid.",
        210503: "Expired agreement condition is invalid.",
        210504: "Unexpired agreement condition is invalid.",
        210601: "Message sender balance is insufficient.",
        220001: "Message sender(exchange contract) isn't latest version.",
        # IbetEscrow (23XXXX)
        230001: "Escrow amount is 0.",
        230002: "Message sender balance is insufficient.",
        230003: "Token status of escrow is inactive.",
        230101: "Target escrow ID is invalid.",
        230102: "Target escrow status is invalid.",
        230103: "Message sender is not escrow sender and escrow agent.",
        230104: "Token status of escrow is inactive.",
        230201: "Target escrow ID is invalid.",
        230202: "Target escrow status is invalid.",
        230203: "Message sender is not escrow agent.",
        230204: "Token status of escrow is inactive.",
        230301: "Message sender balance is insufficient.",
        # IbetSecurityTokenEscrow (24XXXX)
        240001: "Escrow amount is 0.",
        240002: "Message sender balance is insufficient.",
        240003: "Token status of escrow is inactive.",
        240101: "Target escrow ID is invalid.",
        240102: "Target escrow status is invalid.",
        240103: "Message sender is not escrow sender and escrow agent.",
        240104: "Token status of escrow is inactive.",
        240201: "Application doesn't exist.",
        240202: "Message sender is not token owner.",
        240203: "Target escrow status is invalid.",
        240204: "Target escrow status has not been finished.",
        240205: "Token status of escrow is inactive.",
        240301: "Target escrow ID is invalid.",
        240302: "Target escrow status is invalid.",
        240303: "Message sender is not escrow agent.",
        240304: "Token status of escrow is inactive.",
        240401: "Message sender balance is insufficient.",
        # PaymentGateway (30XXXX)
        300001: "Payment account is banned.",
        300101: "Target account address is not registered.",
        300201: "Target account address is not registered.",
        300301: "Target account address is not registered.",
        300401: "Target account address is not registered.",
        300501: "Target account address is not registered.",
        # PersonalInfo (40XXXX)
        400001: "Target account address is not registered.",
        400002: "Target account address is not linked to message sender.",
        # Ownable (50XXXX)
        500001: "Message sender is not contract owner.",
        500101: "New owner address is not set.",
        # ContractRegistry (60XXXX)
        600001: "Target address is not contract address.",
        600002: "Message sender is not contract owner.",
        # E2EMessaging (61XXXX)
        610001: "E2E Message for message owner doesn't exist.",
        610011: "Message sender is not E2E Message sender.",
        # FreezeLog (62XXXX)
        620001: "Log is frozen.",
    }.get(code, "")