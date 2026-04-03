from ..test_helpers import assert_parse_ok


def test_function_param_reference_in_expression():
    root = assert_parse_ok(
        """
        function int triple(int value) {
            int result;
            result = value * 3;
            return result;
        }
        """
    )
    assert root is not None


def test_local_variable_reference():
    root = assert_parse_ok(
        """
        function int test() {
            int local_var;
            int another_var;
            local_var = 10;
            another_var = local_var + 5;
            return another_var;
        }
        """
    )
    assert root is not None


def test_repeat_index_reference():
    root = assert_parse_ok(
        """
        function int loop_sum() {
            int sum;
            sum = 0;
            repeat (i : 10) {
                sum = sum + i;
            }
            return sum;
        }
        """
    )
    assert root is not None


def test_foreach_iterator_reference():
    root = assert_parse_ok(
        """
        function int array_sum(array<int,10> arr) {
            int total;
            total = 0;
            foreach (elem : arr) {
                total = total + elem;
            }
            return total;
        }
        """
    )
    assert root is not None


def test_foreach_index_reference():
    root = assert_parse_ok(
        """
        function int indexed_sum(array<int,10> arr) {
            int total;
            total = 0;
            foreach (elem : arr[idx]) {
                total = total + elem + idx;
            }
            return total;
        }
        """
    )
    assert root is not None


def test_nested_scope_outer_var_reference():
    root = assert_parse_ok(
        """
        function int nested_scopes() {
            int outer;
            outer = 10;
            {
                int inner;
                inner = outer + 5;
            }
            return outer;
        }
        """
    )
    assert root is not None


def test_shadowing_param_with_local_var():
    root = assert_parse_ok(
        """
        function int shadowing(int value) {
            int result;
            {
                int value;
                value = 3;
                result = value;
            }
            return result;
        }
        """
    )
    assert root is not None


def test_exec_action_field_reference():
    root = assert_parse_ok(
        """
        component pss_top {
            action A {
                rand int value;
                int result;

                exec body {
                    result = value + 1;
                }
            }
        }
        """
    )
    assert root is not None
