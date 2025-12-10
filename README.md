## Sabacc con i Tarocchi

In case you're not the same flavor of nerd that I am, Sabacc is a card game from the *Star Wars* universe. In-universe, it's played with electronic cards that can change their values mid-game. Earth technology hasn't gotten to that point yet, but after noticing some similarities between the in-universe deck and a real-world Tarot deck, I decided to write some rules for a version that could be played on our planet. I then set about building a simulator for play-testing the rules and messing around with 8-bit graphics. Yes, I vibe-coded some of it, but I checked Claude's work, just like any responsible senior dev would do with a junior dev. It's not a big deal. Don't worry about it.

## Installation & Perquizzits

I assume you have a standard Python 3 installation. If you want to run the GUI (and why wouldn't you?), make sure you've got `tkinter` installed. There might also be some other dependencies I forgot about. You're smart, you can figure it out. I have no clue if it will work on Windows. If you want to fork the code and port it, be my guest.

## Starting the Program

Git down with your bad self and extract the files to a convenient place of your choosing. After making sure it's executable (with `chmod +x`), simply run `./sabacc` in yer shell. It should fire right up.

## Tweaks / Roadmap for v2.0

The computer will pick opponent names at random from `player_names.md`, which you can feel free to edit. The GUI will default to procedurally-generated elements, but you can substitute yer own graphics according to the instructions in `gui/assets/GUI-README.md`. As I create assets, I'll add them in future commits. Contributions and collaborations welcome! Email me at [devs@neroots.net](mailto:devs@neroots.net). Eventually I'm going to implement different skill levels and play styles for various players, as well as give them all cool 8-bit avatars. Stay tuned, and may the Force be with you!

- PFG
