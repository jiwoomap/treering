# Render with: brew install vhs && vhs docs/media/demo.tape
Output docs/media/demo.gif
Set FontSize 15
Set Width 1100
Set Height 620
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms

Type "ROOT=$(treering demo --log rings.jsonl | tee /dev/tty | head -1 | awk '{print $3}')"
Enter
Sleep 4s
Type "clear"
Enter
Type "treering log rings.jsonl --runs"
Enter
Sleep 3s
Type "treering verify rings.jsonl --key $ROOT"
Enter
Sleep 3s
