"""Tests for the KeyboardSimulator orchestrator."""

import time
import threading
from unittest.mock import MagicMock, call

import pytest

# Since we are in tests/, we need to adjust the path to import from src/
from keyboard_simulator.simulator import KeyboardSimulator, SimulatorHooks
from keyboard_simulator.tasks import SimulationPlan, TypingTask


@pytest.fixture
def mock_backend():
    """Provides a mock AbstractKeyboardBackend."""
    backend = MagicMock()
    backend.type_character = MagicMock()
    return backend


@pytest.fixture
def simple_plan():
    """Provides a simple SimulationPlan for testing."""
    task = TypingTask(description="test", payload="abc")
    return SimulationPlan(
        delay_between_keystrokes=0.01,
        countdown_before_start=0,
        tasks=[task],
    )


def test_run_plan_executes_tasks(mock_backend, simple_plan):
    """Verify that run_plan calls backend.type_character for each character."""
    simulator = KeyboardSimulator(backend=mock_backend)
    simulator.run_plan(simple_plan)

    # Check that type_character was called for 'a', 'b', and 'c'
    calls = [
        call("a", simple_plan.delay_between_keystrokes),
        call("b", simple_plan.delay_between_keystrokes),
        call("c", simple_plan.delay_between_keystrokes),
    ]
    mock_backend.type_character.assert_has_calls(calls, any_order=False)
    assert mock_backend.type_character.call_count == 3


def test_stop_event_terminates_execution(mock_backend):
    """Test that setting the stop_event gracefully stops the simulation."""
    # A long payload to ensure we can stop it mid-execution
    task = TypingTask(description="long task", payload="abcdefghijklmnopqrstuvwxyz")
    plan = SimulationPlan(delay_between_keystrokes=0.1, countdown_before_start=0, tasks=[task])
    simulator = KeyboardSimulator(backend=mock_backend)

    def stop_later():
        # Let a few characters be typed, then stop
        time.sleep(0.25)
        simulator.stop()

    # Run simulation in a separate thread
    simulation_thread = threading.Thread(target=simulator.run_plan, args=(plan,))
    stopper_thread = threading.Thread(target=stop_later)

    simulation_thread.start()
    stopper_thread.start()

    simulation_thread.join(timeout=2)
    stopper_thread.join()

    # The simulation should have stopped after a few characters, not completed the whole alphabet
    assert mock_backend.type_character.call_count < 10
    assert not simulation_thread.is_alive()


def test_pause_and_resume(mock_backend, simple_plan):
    """Test that pause and resume control the flow of execution."""
    simulator = KeyboardSimulator(backend=mock_backend)
    
    # Use a thread to run the plan
    simulation_thread = threading.Thread(target=simulator.run_plan, args=(simple_plan,))
    
    # Start the simulation
    simulation_thread.start()
    
    # Immediately pause
    simulator.pause()
    time.sleep(0.2) # Give it time to process the pause
    
    # At this point, no characters should have been typed
    assert mock_backend.type_character.call_count == 0
    
    # Resume the simulation
    simulator.resume()
    time.sleep(0.2) # Give it time to complete
    
    # Now all characters should have been typed
    assert mock_backend.type_character.call_count == 3
    simulation_thread.join()


def test_hooks_are_called(mock_backend):
    """Verify that on_countdown and on_status hooks are triggered correctly."""
    mock_on_countdown = MagicMock()
    mock_on_status = MagicMock()
    hooks = SimulatorHooks(on_countdown=mock_on_countdown, on_status=mock_on_status)
    
    task = TypingTask(description="test", payload="a")
    plan = SimulationPlan(delay_between_keystrokes=0.01, countdown_before_start=2, tasks=[task])
    
    simulator = KeyboardSimulator(backend=mock_backend, hooks=hooks)
    simulator.run_plan(plan)
    
    # Check countdown hooks
    countdown_calls = [call(2), call(1)]
    mock_on_countdown.assert_has_calls(countdown_calls)
    
    # Check status hooks
    status_calls = [call("running"), call("completed")]
    mock_on_status.assert_has_calls(status_calls)

