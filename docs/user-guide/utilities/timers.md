# Timers

::: frequenz.channels.timer
    options:
        inherited_members: []
        members: []
        show_bases: false
        show_root_heading: false
        show_root_toc_entry: false
        show_source: false

### Policies

#### Skip Missed And Drift

::: frequenz.channels.timer.SkipMissedAndDrift
    options:
        inherited_members: []
        members: []
        show_bases: false
        show_root_heading: false
        show_root_toc_entry: false
        show_source: false

#### Skip Missed And Re-Sync

::: frequenz.channels.timer.SkipMissedAndResync
    options:
        inherited_members: []
        members: []
        show_bases: false
        show_root_heading: false
        show_root_toc_entry: false
        show_source: false

#### Trigger All Missed

::: frequenz.channels.timer.TriggerAllMissed
    options:
        inherited_members: []
        members: []
        show_bases: false
        show_root_heading: false
        show_root_toc_entry: false
        show_source: false

## High-level Interface

::: frequenz.channels.timer.Timer
    options:
        inherited_members: []
        members: []
        show_bases: false
        show_root_heading: false
        show_root_toc_entry: false
        show_source: false


## Low-level Interface

A [`Timer`][frequenz.channels.timer.Timer] can be created using an arbitrary missed
ticks policy by calling the [low-level
constructor][frequenz.channels.timer.Timer.__init__] and passing the policy via the
[`missed_tick_policy`][frequenz.channels.timer.Timer.missed_tick_policy] argument.

### Custom Missed Tick Policies

::: frequenz.channels.timer.MissedTickPolicy
    options:
        inherited_members: []
        members: []
        show_bases: false
        show_root_heading: false
        show_root_toc_entry: false
        show_source: false
