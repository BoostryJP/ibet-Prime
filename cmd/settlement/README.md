# ibet settlement CLI

## Run

### with container

```bash
> docker exec -it -e "TERM=xterm-256color" ibet-prime-app bash --login
> apl@2e5a80e06fcb:/$ settlement-cli --help

 Usage: settlement-cli [OPTIONS] COMMAND [ARGS]...

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                                                                                                                                                                                    │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                                                                                                                                                             │
│ --help                        Show this message and exit.                                                                                                                                                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ abort                                                                                                                                                                                                                                                                      │
│ create_agent                                                                                                                                                                                                                                                               │
│ finish                                                                                                                                                                                                                                                                     │
│ list                                                                                                                                                                                                                                                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Commands

### List

```bash
 Usage: settlement-cli list [OPTIONS] EXCHANGE_ADDRESS AGENT_ADDRESS [STATUS]:[DELIVER
                            Y_CREATED|DELIVERY_CANCELED|DELIVERY_CONFIRMED|DELIVERY_FI
                            NISHED|DELIVERY_ABORTED] [API_URL]

╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    exchange_address      TEXT                                                                                                 [default: None] [required]                                                                                                                 │
│ *    agent_address         TEXT                                                                                                 [default: None] [required]                                                                                                                 │
│      status                [STATUS]:[DELIVERY_CREATED|DELIVERY_CANCELED|DELIVERY_CONFIRMED|DELIVERY_FINISHED|DELIVERY_ABORTED]  [default: delivery_confirmed]                                                                                                              │
│      api_url               [API_URL]                                                                                            [env var: API_URL] [default: http://localhost:5000]                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Finish

```bash
 Usage: settlement-cli finish [OPTIONS] EXCHANGE_ADDRESS AGENT_ADDRESS DELIVERY_ID
                              [EOA_PASSWORD] [API_URL]

╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    exchange_address      TEXT            [default: None] [required]                                                                                                                                                                                                      │
│ *    agent_address         TEXT            [default: None] [required]                                                                                                                                                                                                      │
│ *    delivery_id           INTEGER         [default: None] [required]                                                                                                                                                                                                      │
│      eoa_password          [EOA_PASSWORD]  [env var: EOA_PASSWORD] [default: None]                                                                                                                                                                                         │
│      api_url               [API_URL]       [env var: API_URL] [default: http://localhost:5000]                                                                                                                                                                             │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Abort

```bash
 Usage: settlement-cli abort [OPTIONS] EXCHANGE_ADDRESS AGENT_ADDRESS DELIVERY_ID
                             [EOA_PASSWORD] [API_URL]

╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    exchange_address      TEXT            [default: None] [required]                                                                                                                                                                                                      │
│ *    agent_address         TEXT            [default: None] [required]                                                                                                                                                                                                      │
│ *    delivery_id           INTEGER         [default: None] [required]                                                                                                                                                                                                      │
│      eoa_password          [EOA_PASSWORD]  [env var: EOA_PASSWORD] [default: None]                                                                                                                                                                                         │
│      api_url               [API_URL]       [env var: API_URL] [default: http://localhost:5000]                                                                                                                                                                             │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Create DVP Agent

```bash
 Usage: settlement-cli create_agent [OPTIONS] EOA_PASSWORD [API_URL]

╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    eoa_password      TEXT       [env var: EOA_PASSWORD] [default: None] [required]                                                                                                                                                                                       │
│      api_url           [API_URL]  [env var: API_URL] [default: http://localhost:5000]                                                                                                                                                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```