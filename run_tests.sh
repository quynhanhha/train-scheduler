#!/bin/bash
# Test runner script that runs tests with proper isolation

echo "Running Train Scheduler Test Suite"
echo "================================"
echo ""

# Activate virtual environment if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
fi

# Run tests by category for better isolation
echo "Running Model Tests"
pytest tests/test_models.py -v --tb=short
MODEL_RESULT=$?

echo ""
echo "Running Schema Tests"
pytest tests/test_schemas.py -v --tb=short
SCHEMA_RESULT=$?

echo ""
echo "Running Health Check Test"
pytest tests/test_main.py -v --tb=short
MAIN_RESULT=$?

echo ""
echo "Running Train API Tests"
pytest tests/test_api_trains.py -v --tb=short
TRAIN_RESULT=$?

echo ""
echo "Running Station API Tests"
pytest tests/test_api_stations.py -v --tb=short
STATION_RESULT=$?

echo ""
echo "Running Track Segment API Tests"
pytest tests/test_api_segments.py -v --tb=short
SEGMENT_RESULT=$?

echo ""
echo "Running Trip API Tests"
pytest tests/test_api_trips.py -v --tb=short
TRIP_RESULT=$?

echo ""
echo "Running Conflict Detection Tests"
pytest tests/test_conflicts.py -v --tb=short
CONFLICT_RESULT=$?

echo ""
echo "======================================"
echo "Test Summary:"
echo "======================================"
echo "Model Tests:        $([ $MODEL_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "Schema Tests:       $([ $SCHEMA_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "Health Tests:       $([ $MAIN_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "Train API Tests:    $([ $TRAIN_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "Station API Tests:  $([ $STATION_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "Segment API Tests:  $([ $SEGMENT_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "Trip API Tests:     $([ $TRIP_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "Conflict Tests:     $([ $CONFLICT_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo ""

# Exit with error if any test suite failed
if [ $MODEL_RESULT -ne 0 ] || [ $SCHEMA_RESULT -ne 0 ] || [ $MAIN_RESULT -ne 0 ] || \
   [ $TRAIN_RESULT -ne 0 ] || [ $STATION_RESULT -ne 0 ] || [ $SEGMENT_RESULT -ne 0 ] || \
   [ $TRIP_RESULT -ne 0 ] || [ $CONFLICT_RESULT -ne 0 ]; then
    echo "Some tests failed"
    exit 1
else
    echo "All test suites passed"
    exit 0
fi

