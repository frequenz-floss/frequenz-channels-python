# Multiple Sources

If you need to receive values from multiple sources it can be complicated, as
you probably want to get the first message of each receiver as soon as it is
available. A naive approach like this will not work:

```python
receiver1: Receiver[int] = channel1.new_receiver()
receiver2: Receiver[int] = channel2.new_receiver()

msg = await receiver1.receive()
print(f"Received from channel1: {msg}")

msg = await receiver2.receive()
print(f"Received from channel2: {msg}")
```

The problem is that if the first message is not available in `channel1` but in
`channel2`, the program will be blocked until a message is available in
`channel1`, but you probably want to receive the first message from `channel2`
as soon as it is available.

Frequenz Channels provides two tools to solve this issue:
[`merge()`][frequenz.channels.merge] and
[`select()`][frequenz.channels.select].
