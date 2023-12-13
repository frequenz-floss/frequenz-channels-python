# Channels

A channel is a communication mechanism that allows data (messages) to be
transmitted between different coroutines. It consists of
[senders](../sending.md), which send messages, and
[receivers](../receiving/index.md), which receive those messages. The channel itself
acts as a conduit for these messages.

Conceptually, a channel looks like this:

<center>
```bob
.---------.  Message    .----------.  Message    .-----------.
| Sender  +------------>| Channel  +------------>| Receiver  |
'---------'             '----------'             '-----------'
```
</center>

Besides this simple model, there are many variations of channels depending on
various factors:

* How many senders and receivers can a channel have?

* Do all receivers receive all messages from all senders?

* How many messages can a channel hold (buffered), or can it hold any messages
  at all (unbuffered)?

* What happens if a sender tries to send a message to a full channel?

    * Does the send operation block until the channel has space again?
    * Does it fail?
    * Does it silently drop the message?

Because these questions can have many answers, there are different types of
channels. Frequenz Channels offers a few of them:

* [Anycast](anycast.md)
* [Broadcast](broadcast.md)

More might be added in the future, and you can also create your own.
