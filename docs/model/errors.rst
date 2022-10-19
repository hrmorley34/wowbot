===================
wowbot.model.errors
===================

.. py:module:: wowbot.model.errors


.. autoclass:: BaseModelError

.. autoclass:: ContextModelError

.. autoclass:: ContextFactory

.. attribute:: contextvar

   The default ContextFactory

.. attribute:: context

   A context manager for entering the default context

   .. code-block:: python

      with context("key", 0):
          # the context here is ("key", 0)
          with context("three"):
              # the context is now ("key", 0, "three")
              raise ContextModelError()
              # this error has a context attribute of ("key", 0, "three")

.. autoclass:: ErrorCollection
