# Frequenz Channels Release Notes

## Bug Fixes

* `Timer`: Fix bug that was causing calls to `reset()` to not reset the timer, if the timer was already being awaited.
