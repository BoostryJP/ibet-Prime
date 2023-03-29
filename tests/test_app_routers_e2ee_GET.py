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


class TestAppRoutersE2EEGET:
    # target API endpoint
    apiurl = "/e2ee"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        # request target api
        resp = client.get(self.apiurl)

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "public_key": "-----BEGIN PUBLIC KEY-----\n"
            "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuJ52ArJ9eEGjJdhUHE4c\n"
            "jekmlfNYztqPWMMj/JtfCMR/B0BOqWdrwOQ4eNTv0IgW+5pGPszD8KSctCI1vy47\n"
            "ZjCTPndZp7ypDqUpyVBqonZ3XCpQrjqwHy3Pn1HT3+xiQzTxFxVOQZ7ftQyziviD\n"
            "1vfGzWfZ/Ww5g+y/tEgMbmw8+6XwVMmwPeKtNYM1t9SrPkm27Tvw3upVYL3Pq2hv\n"
            "9pBfM60xV834MkL8KWPdQlTHMJvQ8cRjoAO9kycVe3xN2qq5ShiMGSwaEn5FiC2z\n"
            "iVfprRkMGXgi02K7XunKcmpr56oDk16ltyqvpWJMdqYLzK50JYh+C7ipgk+S4D9y\n"
            "5QIDAQAB\n"
            "-----END PUBLIC KEY-----"
        }

    ###########################################################################
    # Error Case
    ###########################################################################
