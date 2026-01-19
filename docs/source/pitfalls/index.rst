Common Pitfalls
===============

This section documents common mistakes, gotchas, and pitfalls when working
with Routilux. Each pitfall includes symptoms, root causes, solutions, and
prevention strategies.

.. note:: **Why This Section Matters**

   Understanding these pitfalls will help you:
   - Avoid hours of debugging
   - Write more reliable workflows
   - Design better architectures
   - Troubleshoot issues faster

.. tip:: **How to Use This Section**

   - **Before coding**: Read relevant pitfalls to avoid mistakes
   - **While debugging**: Match symptoms to find solutions
   - **During review**: Check code against known pitfalls
   - **For onboarding**: Train new team members

Pitfalls by Category
--------------------

.. toctree::
   :maxdepth: 1

   routine_design
   state_management
   concurrency
   error_handling
   performance
   serialization

Quick Reference
---------------

Most Common Pitfalls:

1. **Constructor Parameters in Routines** - :doc:`routine_design`
   Routines MUST NOT accept constructor parameters

2. **Confusing WorkerState vs JobContext** - :doc:`state_management`
   WorkerState is persistent, JobContext is temporary

3. **Race Conditions on Shared State** - :doc:`concurrency`
   Concurrent access needs proper synchronization

4. **Unhandled Exceptions** - :doc:`error_handling`
   Unhandled errors fail jobs silently

5. **Over-Engineering** - :doc:`performance`
   Complex designs add unnecessary overhead

6. **Non-Serializable State** - :doc:`serialization`
   WorkerState must contain serializable data only

Pitfall Format
--------------

Each pitfall follows this structure:

**The Pitfall**
- Description of the mistake
- Code example showing the wrong approach

**Why It Happens**
- Root cause explanation
- Common scenarios that lead to the pitfall

**Symptoms**
- How to recognize when you've hit the pitfall
- Error messages, unexpected behavior, performance issues

**Solution**
- Correct code example
- Step-by-step fix

**Prevention**
- Best practices to avoid the pitfall
- Code patterns and architectural guidelines

**Related**
- Cross-references to related pitfalls
- Links to relevant documentation

Contributing
------------

Found a new pitfall? Please contribute!

1. Document the pitfall with examples
2. Include symptoms and solutions
3. Add cross-references
4. Submit a pull request

.. seealso::

   :doc:`../user_guide/troubleshooting`
      Troubleshooting guide for common issues

   :doc:`../tutorial/index`
      Progressive tutorials that avoid these pitfalls
