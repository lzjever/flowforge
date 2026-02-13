"""
Complete error handling examples for Routilux.
"""

from routilux.core import (
    ErrorHandler,
    ErrorStrategy,
    Routine,
    Flow,
)


# Example 1: Optional routine with CONTINUE
class OptionalEnrichmentRoutine(Routine):
    """Optional data enrichment that shouldn't block the workflow."""

    def setup(self):
        self.add_slot("input")
        self.add_event("output")

    def logic(self, input_data, **kwargs):
        try:
            # Call external API that might fail
            enriched = self._call_enrichment_api(input_data)
            self.emit("output", **enriched)
        except Exception:
            # Let CONTINUE strategy handle this
            raise


def optional_routine_example():
    """Example: Mark routine as optional."""
    flow = Flow()

    routine = OptionalEnrichmentRoutine()
    routine.set_error_handler(ErrorHandler(strategy=ErrorStrategy.CONTINUE))
    flow.add_routine(routine, "enricher")


# Example 2: Critical routine with RETRY
class CriticalAPICall(Routine):
    """Critical API call that must succeed."""

    def setup(self):
        self.add_slot("input")
        self.add_event("output")

    def logic(self, input_data, **kwargs):
        # Call critical API
        result = self._call_critical_api(input_data)
        self.emit("output", **result)


def critical_routine_example():
    """Example: Mark routine as critical with retry."""
    flow = Flow()

    routine = CriticalAPICall()
    routine.set_error_handler(
        ErrorHandler(
            strategy=ErrorStrategy.RETRY,
            max_retries=5,
            retry_delay=2.0,
        )
    )
    flow.add_routine(routine, "caller")


# Example 3: Flow-level default handler
def flow_level_handler_example():
    """Example: Set default error handling for entire flow."""
    flow = Flow()

    # Set CONTINUE as default for all routines
    flow.set_error_handler(ErrorHandler(strategy=ErrorStrategy.CONTINUE))

    # Individual routines can override
    critical = CriticalAPICall()
    critical.set_error_handler(ErrorHandler(strategy=ErrorStrategy.STOP))
    flow.add_routine(critical, "critical")
