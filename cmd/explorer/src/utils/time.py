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
from collections import OrderedDict
from datetime import datetime

INTERVALS = OrderedDict(
    [
        ("year", 31536000),  # 60 * 60 * 24 * 365
        ("month", 2627424),  # 60 * 60 * 24 * 30.41 (assuming 30.41 days in a month)
        ("week", 604800),  # 60 * 60 * 24 * 7
        ("day", 86400),  # 60 * 60 * 24
        ("hr", 3600),  # 60 * 60
        ("minute", 60),
        ("sec", 1),
    ]
)


def human_time(secs: int):
    """Human-readable time from secs (ie. 5 days and 2 hrs).
    Examples:
        >>> human_time(15)
        "less than minutes"
        >>> human_time(3600)
        "1 hr"
        >>> human_time(3720)
        "1 hr"
        >>> human_time(266400)
        "3 days"
        >>> human_time(0)
        "0 secs"
        >>> human_time(1)
        "less than minutes"
    Args:
        secs (int): Duration in secs.
    Returns:
        str: Human-readable time.
    """
    if secs < 0:
        return "0 secs"
    elif secs == 0:
        return "0 secs"
    elif 1 < secs < INTERVALS["minute"]:
        return "less than minutes"

    res = []
    for interval, count in INTERVALS.items():
        quotient, remainder = divmod(secs, count)
        if quotient >= 1:
            secs = remainder
            if quotient > 1:
                interval += "s"
            res.append("%i %s" % (int(quotient), interval))
        if remainder == 0:
            break

    return res[0]


def unix_to_iso(unix_time: int):
    return datetime.fromtimestamp(unix_time).isoformat()
