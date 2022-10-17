===========
sounds.json
===========

This file describes the playable sounds.

-------
Example
-------

.. literalinclude:: /../tests/sounds/sounds.json
   :language: JSON

This defines two sounds:

- :code:`s.example`, which has a
   - 1/4 chance of playing :code:`example1.opus`
   - 1/4 chance of :code:`example2.opus`
   - 2/4 chance of playing a random one out of :code:`example3.opus` and :code:`example4.opus`
      - The weight of 2 makes it twice the other two
      - Each of those files has a 1/2 × 2/4 = 1/4 chance overall
- :code:`s.mysound`, which has a
   - 9/10 chance of playing a random file matching the pattern :code:`mysound-*.opus`
      - That's 9/20 for :code:`mysound-a.opus` and 9/20 for :code:`mysound-b.opus`
   - 1/10 chance of playing a random file matching the pattern :code:`mysound2-*.opus`
      - That's 1/20 for :code:`mysound2-x.opus` and 1/20 for :code:`mysound2-y.opus`
