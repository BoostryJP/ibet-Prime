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

import logging
import os

from gunicorn.app.wsgiapp import run
from gunicorn.arbiter import Arbiter

if __name__ == "__main__":

    class SupressSigtermFilter(logging.Filter):
        def filter(self, record):
            if record.levelname == "ERROR" and "was sent SIGTERM" in record.msg:
                return False
            return True

    # monkey patch for setup method of gunicorn.arbiter.Arbiter
    def setup(self, app):
        self.app = app
        self.cfg = app.cfg

        if self.log is None:
            self.log = self.cfg.logger_class(app.cfg)
            self.log.error_log.addFilter(SupressSigtermFilter())

        # reopen files
        if "GUNICORN_FD" in os.environ:
            self.log.reopen_files()

        self.worker_class = self.cfg.worker_class
        self.address = self.cfg.address
        self.num_workers = self.cfg.workers
        self.timeout = self.cfg.timeout
        self.proc_name = self.cfg.proc_name

        self.log.debug(
            "Current configuration:\n{0}".format(
                "\n".join(
                    "  {0}: {1}".format(config, value.value)
                    for config, value in sorted(
                        self.cfg.settings.items(), key=lambda setting: setting[1]
                    )
                )
            )
        )

        # set environment' variables
        if self.cfg.env:
            for k, v in self.cfg.env.items():
                os.environ[k] = v

        if self.cfg.preload_app:
            self.app.wsgi()

    # monkey patch
    Arbiter.setup = setup
    run(prog="gunicorn")
