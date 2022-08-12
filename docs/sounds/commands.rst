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
- :code:`/mytoplevelcommand mysubcommand`
- :code:`/mytoplevelcommand myothercommand {sound}`, which has an option called :code:`sound` which can be :code:`My Sound` or :code:`Example`
