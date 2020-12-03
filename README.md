# If you are here through the Discord pin, i recommend scrolling one pinned message lower for instructions on how to run this on Merlin. It's easier.

# Usage
Strictly requires Linux. Merlin is fine, at `/homes/eva/xd/xditej01/Projects/9e45e5b2/runIZP2tests.sh` there is a utility script for launching these.
Just call that script from within a directory you have your `sps.c` file inside.
If you want to just see results, create a `sps.c` file with just the contents `int main() {return 0;}` inside.

Run the python file to see a help message, and provide it with required arguments to automatically run all tests.
Running it with the `-mc` flag is hugely recommended, to check you are not leaking any memory anywhere.

If you want to add your own tests, just add them to `tests.json`

# Disclaimer
Sorry for Merlin's semi-outage on tuesday, the tester had a bug preventing it from succesfully killing zombies :( All should be fixed now!
