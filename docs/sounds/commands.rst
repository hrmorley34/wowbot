=============
commands.json
=============

This file describes the slash commands.

-------
Example
-------

.. literalinclude:: /../tests/sounds/commands.json
  :language: JSON

This creates the commands:

- :code:`/mycommand`
- :code:`/command2 [option]`, where :code:`option` can be either :code:`Option 1` (default) or :code:`Option 2`
- :code:`/mytoplevelcommand mysubcommand`, which is *not* accessible to the user with id :code:`123456781234567890`
- :code:`/mytoplevelcommand myothercommand {sound}`, which is *only* accessible to users with the role :code:`123456781234567890` or :code:`987654321087654321`, and has an option called :code:`sound` which can be :code:`My Sound` or :code:`Example`
