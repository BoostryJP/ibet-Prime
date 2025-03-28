# ibet blockchain explorer

## Run

### with container

```bash
> docker exec -it -e "TERM=xterm-256color" ibet-prime-app bash --login
> apl@2e5a80e06fcb:/$ ibet-explorer --help

 Usage: ibet-explorer [OPTIONS]

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --url                       TEXT                             ibet-Prime server URL to connect [default: http://localhost:5000]                                                                               │
│ --lot-size                  INTEGER                          Lot size to fetch Block Data list [default: 100]                                                                                                │
│ --install-completion        [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. [default: None]                                                                                     │
│ --show-completion           [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to copy it or customize the installation. [default: None]                                              │
│ --help                                                       Show this message and exit.                                                                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

- **URL**: ibet-Prime URL.
- You can run this on pythonic way in local.

## Screenshots 👀

![query-setting](https://user-images.githubusercontent.com/15183665/222354993-0c11eedc-fb22-472a-8c9f-f9bc8be4d173.png)

![block](https://user-images.githubusercontent.com/15183665/222355008-0c893524-2a80-4975-9c44-537649b11fc7.png)

![transaction](https://user-images.githubusercontent.com/15183665/222355025-24b72685-8d27-48e5-9ea1-b265c4365629.png)

