# Output setup (Ubuntu, GNOME, Wayland)

On GNOME/Wayland, `pynput`/`xdotool` cannot type into other apps and `wtype`
does not work (Mutter lacks the virtual-keyboard protocol). We use **ydotool**,
which injects input through `/dev/uinput`.

Backends: `clipboard` (default), `ydotool`, `stdout`.

- `clipboard`: `wl-copy` the text, then press the paste chord. Handles Unicode
  and any keyboard layout. Recommended.
- `ydotool`: `ydotool type`. US layout and ASCII only.
- `stdout`: prints actions; no typing. Use it to test the pipeline.

## 1. Install

```bash
sudo apt install ydotool wl-clipboard
ydotool --help | head -5
```

Ubuntu's packaged ydotool may be the old 0.1.x (key syntax `ydotool key ctrl+v`).
This code defaults to the 1.x syntax (keycodes, `ydotool key 29:1 47:1 47:0 29:0`).
If you have 0.1.x, set `ydotool_syntax = "names"`, or build 1.x:

```bash
sudo apt install build-essential cmake git libboost-program-options-dev scdoc
git clone https://github.com/ReimuNotMoe/ydotool && cd ydotool
cmake -B build && cmake --build build
sudo cmake --install build   # installs ydotool and ydotoold to /usr/local/bin
```

## 2. Allow access to /dev/uinput

```bash
echo 'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
  | sudo tee /etc/udev/rules.d/60-uinput.rules
sudo usermod -aG input "$USER"
sudo udevadm control --reload-rules && sudo udevadm trigger
# log out and back in so the group change applies
```

Trade-off: anything running as you (member of `input`) can then inject
keystrokes into your session.

## 3. Run ydotoold as a user service

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/ydotoold.service <<'UNIT'
[Unit]
Description=ydotool daemon

[Service]
ExecStart=/usr/local/bin/ydotoold
Restart=on-failure

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now ydotoold
```

Adjust `ExecStart` to `/usr/bin/ydotoold` for the apt package. If the socket
is not at `/run/user/<uid>/.ydotool_socket`, export `YDOTOOL_SOCKET` to its path
for both the daemon and KeyWhisperer.

## 4. Check

```bash
python -c "from keywhisperer.output import check_environment as c; print(c().format())"
```

## Options (output config)

| key | default | meaning |
| --- | --- | --- |
| `paste_keys` | `["ctrl","v"]` | paste chord; terminals usually need `["ctrl","shift","v"]` |
| `copy_delay` | `0.05` | seconds between `wl-copy` and paste |
| `restore_clipboard` | `false` | put the previous text clipboard back afterwards |
| `restore_delay` | `0.3` | seconds to wait before restoring |
| `ydotool_syntax` | `"keycodes"` | `"keycodes"` (1.x) or `"names"` (0.1.x) |
| `key_delay_ms` | unset | `--key-delay` for `ydotool key` (1.x) |
| `type_delay_ms` | `12` | `--key-delay` for `ydotool type` |

Restoring only works for text clipboards; an image on the clipboard is left
replaced by the dictated text.
