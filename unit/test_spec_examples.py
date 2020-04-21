
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

'''
Created on Feb 16, 2020

@author: ballance
'''
from unittest.case import TestCase
import pss_spec_examples
import sys
from pssparser.cu_parser import CUParser
from antlr4.InputStream import InputStream
from _io import StringIO

class TestSpecExamples(TestCase):
    
    def _runTest(self, text, name):
        input_stream = InputStream(text)
        parser = CUParser(input_stream, name)
        cu = parser.parse()
        
        if len(cu.markers) > 0:
            print("Test Failed:")
            in_reader = StringIO(text)
            i=1
            while True:
                line = in_reader.readline()
                if line == "":
                    break
                line = line[:-1]
                print("%3d: %s" % (i, line))
                i+=1
        
        self.assertEqual(len(cu.markers), 0, "Errors")
        
    def setUp(self):
        super().setUp()
        print("--> " + self._testMethodName + "********************************")
        sys.stdout.flush()
        
    def tearDown(self):
        print("<-- " + self._testMethodName + "********************************")
        sys.stdout.flush()
        super().tearDown()
    
    #****************************************************************
    #* 003_enum_data_type.pss
    #****************************************************************
    def test_003_enum_data_type(self):
        self._runTest(
            pss_spec_examples.spec_ex_003_enum_data_type,
            "003_enum_data_type.pss");

    #****************************************************************
    #* 005_string_data_type.pss
    #****************************************************************
    def test_005_string_data_type(self):
        self._runTest(
            pss_spec_examples.spec_ex_005_string_data_type,
            "005_string_data_type.pss");

    #****************************************************************
    #* 007_chandle_data_type.pss
    #****************************************************************
    def test_007_chandle_data_type(self):
        self._runTest(
            pss_spec_examples.spec_ex_007_chandle_data_type,
            "007_chandle_data_type.pss");

    #****************************************************************
    #* 008_struct_with_rand_modifier.pss
    #****************************************************************
    def test_008_struct_with_rand_modifier(self):
        self._runTest(
            pss_spec_examples.spec_ex_008_struct_with_rand_modifier,
            "008_struct_with_rand_modifier.pss");

    #****************************************************************
    #* 010_typedef.pss
    #****************************************************************
    def test_010_typedef(self):
        self._runTest(
            pss_spec_examples.spec_ex_010_typedef,
            "010_typedef.pss");

    #****************************************************************
    #* 012_fixed_size_arrays.pss
    #****************************************************************
    def test_012_fixed_size_arrays(self):
        self._runTest(
            pss_spec_examples.spec_ex_012_fixed_size_arrays,
            "012_fixed_size_arrays.pss");

    #****************************************************************
    #* 014_sum_property_of_an_array.pss
    #****************************************************************
    def test_014_sum_property_of_an_array(self):
        self._runTest(
            pss_spec_examples.spec_ex_014_sum_property_of_an_array,
            "014_sum_property_of_an_array.pss");

    #****************************************************************
    #* 017_size_property_of_an_array.pss
    #****************************************************************
    def test_017_size_property_of_an_array(self):
        self._runTest(
            pss_spec_examples.spec_ex_017_size_property_of_an_array,
            "017_size_property_of_an_array.pss");

    #****************************************************************
    #* 018_per_attribute_access_modifier.pss
    #****************************************************************
    def test_018_per_attribute_access_modifier(self):
        self._runTest(
            pss_spec_examples.spec_ex_018_per_attribute_access_modifier,
            "018_per_attribute_access_modifier.pss");

    #****************************************************************
    #* 019_block_access_modifier.pss
    #****************************************************************
    def test_019_block_access_modifier(self):
        self._runTest(
            pss_spec_examples.spec_ex_019_block_access_modifier,
            "019_block_access_modifier.pss");

    #****************************************************************
    #* 020_overlap_of_possible_enum_values.pss
    #****************************************************************
    def test_020_overlap_of_possible_enum_values(self):
        self._runTest(
            pss_spec_examples.spec_ex_020_overlap_of_possible_enum_values,
            "020_overlap_of_possible_enum_values.pss");

    #****************************************************************
    #* 021_casting_of_variable_to_a_vector.pss
    #****************************************************************
    def test_021_casting_of_variable_to_a_vector(self):
        self._runTest(
            pss_spec_examples.spec_ex_021_casting_of_variable_to_a_vector,
            "021_casting_of_variable_to_a_vector.pss");

    #****************************************************************
    #* 022_component.pss
    #****************************************************************
    def test_022_component(self):
        self._runTest(
            pss_spec_examples.spec_ex_022_component,
            "022_component.pss");

    #****************************************************************
    #* 024_namespace.pss
    #****************************************************************
    def test_024_namespace(self):
        self._runTest(
            pss_spec_examples.spec_ex_024_namespace,
            "024_namespace.pss");

    #****************************************************************
    #* 026_component_instantiation.pss
    #****************************************************************
    def test_026_component_instantiation(self):
        self._runTest(
            pss_spec_examples.spec_ex_026_component_instantiation,
            "026_component_instantiation.pss");

    #****************************************************************
    #* 028_constraining_a_comp_attribute.pss
    #****************************************************************
    def test_028_constraining_a_comp_attribute(self):
        self._runTest(
            pss_spec_examples.spec_ex_028_constraining_a_comp_attribute,
            "028_constraining_a_comp_attribute.pss");

    #****************************************************************
    #* 030_atomic_action.pss
    #****************************************************************
    def test_030_atomic_action(self):
        self._runTest(
            pss_spec_examples.spec_ex_030_atomic_action,
            "030_atomic_action.pss");

    #****************************************************************
    #* 032_compound_action.pss
    #****************************************************************
    def test_032_compound_action(self):
        self._runTest(
            pss_spec_examples.spec_ex_032_compound_action,
            "032_compound_action.pss");

    #****************************************************************
    #* 034_extended_action_traversal.pss
    #****************************************************************
    def test_034_extended_action_traversal(self):
        self._runTest(
            pss_spec_examples.spec_ex_034_extended_action_traversal,
            "034_extended_action_traversal.pss");

    #****************************************************************
    #* 035_hand_coded_action_traversal.pss
    #****************************************************************
    def test_035_hand_coded_action_traversal(self):
        self._runTest(
            pss_spec_examples.spec_ex_035_hand_coded_action_traversal,
            "035_hand_coded_action_traversal.pss");

    #****************************************************************
    #* 036_inheritance_and_traversal.pss
    #****************************************************************
    def test_036_inheritance_and_traversal(self):
        self._runTest(
            pss_spec_examples.spec_ex_036_inheritance_and_traversal,
            "036_inheritance_and_traversal.pss");

    #****************************************************************
    #* 037_action_traversal.pss
    #****************************************************************
    def test_037_action_traversal(self):
        self._runTest(
            pss_spec_examples.spec_ex_037_action_traversal,
            "037_action_traversal.pss");

    #****************************************************************
    #* 039_anonymous_action_traversal.pss
    #****************************************************************
    def test_039_anonymous_action_traversal(self):
        self._runTest(
            pss_spec_examples.spec_ex_039_anonymous_action_traversal,
            "039_anonymous_action_traversal.pss");

    #****************************************************************
    #* 041_compound_action_traversal.pss
    #****************************************************************
    def test_041_compound_action_traversal(self):
        self._runTest(
            pss_spec_examples.spec_ex_041_compound_action_traversal,
            "041_compound_action_traversal.pss");

    #****************************************************************
    #* 043_sequential_block.pss
    #****************************************************************
    def test_043_sequential_block(self):
        self._runTest(
            pss_spec_examples.spec_ex_043_sequential_block,
            "043_sequential_block.pss");

    #****************************************************************
    #* 045_variants_of_specifying_sequential_execution_in_activity.pss
    #****************************************************************
    def test_045_variants_of_specifying_sequential_execution_in_activity(self):
        self._runTest(
            pss_spec_examples.spec_ex_045_variants_of_specifying_sequential_execution_in_activity,
            "045_variants_of_specifying_sequential_execution_in_activity.pss");

    #****************************************************************
    #* 047_parallel_statement.pss
    #****************************************************************
    def test_047_parallel_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_047_parallel_statement,
            "047_parallel_statement.pss");

    #****************************************************************
    #* 049_another_parallel_statement.pss
    #****************************************************************
    def test_049_another_parallel_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_049_another_parallel_statement,
            "049_another_parallel_statement.pss");

    #****************************************************************
    #* 051_schedule_statement.pss
    #****************************************************************
    def test_051_schedule_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_051_schedule_statement,
            "051_schedule_statement.pss");

    #****************************************************************
    #* 053_scheduling_block_with_sequential_sub_blocks.pss
    #****************************************************************
    def test_053_scheduling_block_with_sequential_sub_blocks(self):
        self._runTest(
            pss_spec_examples.spec_ex_053_scheduling_block_with_sequential_sub_blocks,
            "053_scheduling_block_with_sequential_sub_blocks.pss");

    #****************************************************************
    #* 055_repeat_statement.pss
    #****************************************************************
    def test_055_repeat_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_055_repeat_statement,
            "055_repeat_statement.pss");

    #****************************************************************
    #* 057_another_repeat_statement.pss
    #****************************************************************
    def test_057_another_repeat_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_057_another_repeat_statement,
            "057_another_repeat_statement.pss");

    #****************************************************************
    #* 059_repeat_while_statement.pss
    #****************************************************************
    def test_059_repeat_while_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_059_repeat_while_statement,
            "059_repeat_while_statement.pss");

    #****************************************************************
    #* 061_foreach_statement.pss
    #****************************************************************
    def test_061_foreach_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_061_foreach_statement,
            "061_foreach_statement.pss");

    #****************************************************************
    #* 063_select_statement.pss
    #****************************************************************
    def test_063_select_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_063_select_statement,
            "063_select_statement.pss");

    #****************************************************************
    #* 065_select_statement_with_guard_conditions_and_weights.pss
    #****************************************************************
    def test_065_select_statement_with_guard_conditions_and_weights(self):
        self._runTest(
            pss_spec_examples.spec_ex_065_select_statement_with_guard_conditions_and_weights,
            "065_select_statement_with_guard_conditions_and_weights.pss");

    #****************************************************************
    #* 067_if_else_statement.pss
    #****************************************************************
    def test_067_if_else_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_067_if_else_statement,
            "067_if_else_statement.pss");

    #****************************************************************
    #* 069_match_statement.pss
    #****************************************************************
    def test_069_match_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_069_match_statement,
            "069_match_statement.pss");

    #****************************************************************
    #* 071_using_a_symbol.pss
    #****************************************************************
    def test_071_using_a_symbol(self):
        self._runTest(
            pss_spec_examples.spec_ex_071_using_a_symbol,
            "071_using_a_symbol.pss");

    #****************************************************************
    #* 073_using_a_parameterized_symbol.pss
    #****************************************************************
    def test_073_using_a_parameterized_symbol(self):
        self._runTest(
            pss_spec_examples.spec_ex_073_using_a_parameterized_symbol,
            "073_using_a_parameterized_symbol.pss");

    #****************************************************************
    #* 075_scoping_and_named_sub_activities.pss
    #****************************************************************
    def test_075_scoping_and_named_sub_activities(self):
        self._runTest(
            pss_spec_examples.spec_ex_075_scoping_and_named_sub_activities,
            "075_scoping_and_named_sub_activities.pss");

    #****************************************************************
    #* 076_hierarchical_references_and_named_subactivities.pss
    #****************************************************************
    def test_076_hierarchical_references_and_named_subactivities(self):
        self._runTest(
            pss_spec_examples.spec_ex_076_hierarchical_references_and_named_subactivities,
            "076_hierarchical_references_and_named_subactivities.pss");

    #****************************************************************
    #* 077_bind_statement.pss
    #****************************************************************
    def test_077_bind_statement(self):
        self._runTest(
            pss_spec_examples.spec_ex_077_bind_statement,
            "077_bind_statement.pss");

    #****************************************************************
    #* 079_hierarchical_flow_binding.pss
    #****************************************************************
    def test_079_hierarchical_flow_binding(self):
        self._runTest(
            pss_spec_examples.spec_ex_079_hierarchical_flow_binding,
            "079_hierarchical_flow_binding.pss");

    #****************************************************************
    #* 081_hierarchical_resource_binding.pss
    #****************************************************************
    def test_081_hierarchical_resource_binding(self):
        self._runTest(
            pss_spec_examples.spec_ex_081_hierarchical_resource_binding,
            "081_hierarchical_resource_binding.pss");

    #****************************************************************
    #* 083_buffer_object.pss
    #****************************************************************
    def test_083_buffer_object(self):
        self._runTest(
            pss_spec_examples.spec_ex_083_buffer_object,
            "083_buffer_object.pss");

    #****************************************************************
    #* 085_stream_object.pss
    #****************************************************************
    def test_085_stream_object(self):
        self._runTest(
            pss_spec_examples.spec_ex_085_stream_object,
            "085_stream_object.pss");

    #****************************************************************
    #* 087_state_object.pss
    #****************************************************************
    def test_087_state_object(self):
        self._runTest(
            pss_spec_examples.spec_ex_087_state_object,
            "087_state_object.pss");

    #****************************************************************
    #* 089_buffer_flow_object.pss
    #****************************************************************
    def test_089_buffer_flow_object(self):
        self._runTest(
            pss_spec_examples.spec_ex_089_buffer_flow_object,
            "089_buffer_flow_object.pss");

    #****************************************************************
    #* 091_stream_flow_object.pss
    #****************************************************************
    def test_091_stream_flow_object(self):
        self._runTest(
            pss_spec_examples.spec_ex_091_stream_flow_object,
            "091_stream_flow_object.pss");

    #****************************************************************
    #* 093_declaring_a_resource.pss
    #****************************************************************
    def test_093_declaring_a_resource(self):
        self._runTest(
            pss_spec_examples.spec_ex_093_declaring_a_resource,
            "093_declaring_a_resource.pss");

    #****************************************************************
    #* 095_resource_object.pss
    #****************************************************************
    def test_095_resource_object(self):
        self._runTest(
            pss_spec_examples.spec_ex_095_resource_object,
            "095_resource_object.pss");

    #****************************************************************
    #* 097_pool_declaration.pss
    #****************************************************************
    def test_097_pool_declaration(self):
        self._runTest(
            pss_spec_examples.spec_ex_097_pool_declaration,
            "097_pool_declaration.pss");

    #****************************************************************
    #* 099_static_binding.pss
    #****************************************************************
    def test_099_static_binding(self):
        self._runTest(
            pss_spec_examples.spec_ex_099_static_binding,
            "099_static_binding.pss");

    #****************************************************************
    #* 101_pool_binding.pss
    #****************************************************************
    def test_101_pool_binding(self):
        self._runTest(
            pss_spec_examples.spec_ex_101_pool_binding,
            "101_pool_binding.pss");

    #****************************************************************
    #* 103_resource_object_assignment.pss
    #****************************************************************
    def test_103_resource_object_assignment(self):
        self._runTest(
            pss_spec_examples.spec_ex_103_resource_object_assignment,
            "103_resource_object_assignment.pss");

    #****************************************************************
    #* 105_state_object_binding.pss
    #****************************************************************
    def test_105_state_object_binding(self):
        self._runTest(
            pss_spec_examples.spec_ex_105_state_object_binding,
            "105_state_object_binding.pss");

    #****************************************************************
    #* 107_declaring_a_static_constraint.pss
    #****************************************************************
    def test_107_declaring_a_static_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_107_declaring_a_static_constraint,
            "107_declaring_a_static_constraint.pss");

    #****************************************************************
    #* 109_declaring_a_dynamic_constraint.pss
    #****************************************************************
    def test_109_declaring_a_dynamic_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_109_declaring_a_dynamic_constraint,
            "109_declaring_a_dynamic_constraint.pss");

    #****************************************************************
    #* 111_declaring_a_dynamic_constraint_inside_a_static_constraint.pss
    #****************************************************************
    def test_111_declaring_a_dynamic_constraint_inside_a_static_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_111_declaring_a_dynamic_constraint_inside_a_static_constraint,
            "111_declaring_a_dynamic_constraint_inside_a_static_constraint.pss");

    #****************************************************************
    #* 113_inheriting_and_overriding_constraints.pss
    #****************************************************************
    def test_113_inheriting_and_overriding_constraints(self):
        self._runTest(
            pss_spec_examples.spec_ex_113_inheriting_and_overriding_constraints,
            "113_inheriting_and_overriding_constraints.pss");

    #****************************************************************
    #* 115_action_traversal_in_line_constraint.pss
    #****************************************************************
    def test_115_action_traversal_in_line_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_115_action_traversal_in_line_constraint,
            "115_action_traversal_in_line_constraint.pss");

    #****************************************************************
    #* 117_variable_resolution_inside_with_constraint_block.pss
    #****************************************************************
    def test_117_variable_resolution_inside_with_constraint_block(self):
        self._runTest(
            pss_spec_examples.spec_ex_117_variable_resolution_inside_with_constraint_block,
            "117_variable_resolution_inside_with_constraint_block.pss");

    #****************************************************************
    #* 119_in_constraint.pss
    #****************************************************************
    def test_119_in_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_119_in_constraint,
            "119_in_constraint.pss");

    #****************************************************************
    #* 121_implication_constraint.pss
    #****************************************************************
    def test_121_implication_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_121_implication_constraint,
            "121_implication_constraint.pss");

    #****************************************************************
    #* 123_if_constraint.pss
    #****************************************************************
    def test_123_if_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_123_if_constraint,
            "123_if_constraint.pss");

    #****************************************************************
    #* 125_foreach_iterative_constraint.pss
    #****************************************************************
    def test_125_foreach_iterative_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_125_foreach_iterative_constraint,
            "125_foreach_iterative_constraint.pss");

    #****************************************************************
    #* 127_unique_constraint.pss
    #****************************************************************
    def test_127_unique_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_127_unique_constraint,
            "127_unique_constraint.pss");

    #****************************************************************
    #* 129_scheduling_constraints.pss
    #****************************************************************
    def test_129_scheduling_constraints(self):
        self._runTest(
            pss_spec_examples.spec_ex_129_scheduling_constraints,
            "129_scheduling_constraints.pss");

    #****************************************************************
    #* 130_sequencing_constraint.pss
    #****************************************************************
    def test_130_sequencing_constraint(self):
        self._runTest(
            pss_spec_examples.spec_ex_130_sequencing_constraint,
            "130_sequencing_constraint.pss");

    #****************************************************************
    #* 132_struct_rand_and_non_rand_fields.pss
    #****************************************************************
    def test_132_struct_rand_and_non_rand_fields(self):
        self._runTest(
            pss_spec_examples.spec_ex_132_struct_rand_and_non_rand_fields,
            "132_struct_rand_and_non_rand_fields.pss");

    #****************************************************************
    #* 134_action_rand_qualified_fields.pss
    #****************************************************************
    def test_134_action_rand_qualified_fields(self):
        self._runTest(
            pss_spec_examples.spec_ex_134_action_rand_qualified_fields,
            "134_action_rand_qualified_fields.pss");

    #****************************************************************
    #* 136_action_qualified_data_fields.pss
    #****************************************************************
    def test_136_action_qualified_data_fields(self):
        self._runTest(
            pss_spec_examples.spec_ex_136_action_qualified_data_fields,
            "136_action_qualified_data_fields.pss");

    #****************************************************************
    #* 138_randomizing_flow_object_attributes.pss
    #****************************************************************
    def test_138_randomizing_flow_object_attributes(self):
        self._runTest(
            pss_spec_examples.spec_ex_138_randomizing_flow_object_attributes,
            "138_randomizing_flow_object_attributes.pss");

    #****************************************************************
    #* 140_randomizing_resource_object_attributes.pss
    #****************************************************************
    def test_140_randomizing_resource_object_attributes(self):
        self._runTest(
            pss_spec_examples.spec_ex_140_randomizing_resource_object_attributes,
            "140_randomizing_resource_object_attributes.pss");

    #****************************************************************
    #* 142_activity_with_random_fields.pss
    #****************************************************************
    def test_142_activity_with_random_fields(self):
        self._runTest(
            pss_spec_examples.spec_ex_142_activity_with_random_fields,
            "142_activity_with_random_fields.pss");

    #****************************************************************
    #* 144_activity_with_random_fields_in_a_loop.pss
    #****************************************************************
    def test_144_activity_with_random_fields_in_a_loop(self):
        self._runTest(
            pss_spec_examples.spec_ex_144_activity_with_random_fields_in_a_loop,
            "144_activity_with_random_fields_in_a_loop.pss");

    #****************************************************************
    #* 146_struct_with_random_fields.pss
    #****************************************************************
    def test_146_struct_with_random_fields(self):
        self._runTest(
            pss_spec_examples.spec_ex_146_struct_with_random_fields,
            "146_struct_with_random_fields.pss");

    #****************************************************************
    #* 148_activity_with_random_fields.pss
    #****************************************************************
    def test_148_activity_with_random_fields(self):
        self._runTest(
            pss_spec_examples.spec_ex_148_activity_with_random_fields,
            "148_activity_with_random_fields.pss");

    #****************************************************************
    #* 150_sub_activity_traversal.pss
    #****************************************************************
    def test_150_sub_activity_traversal(self):
        self._runTest(
            pss_spec_examples.spec_ex_150_sub_activity_traversal,
            "150_sub_activity_traversal.pss");

    #****************************************************************
    #* 152_activity_with_dynamic_constraints.pss
    #****************************************************************
    def test_152_activity_with_dynamic_constraints(self):
        self._runTest(
            pss_spec_examples.spec_ex_152_activity_with_dynamic_constraints,
            "152_activity_with_dynamic_constraints.pss");

    #****************************************************************
    #* 154_pre_solve_post_solve.pss
    #****************************************************************
    def test_154_pre_solve_post_solve(self):
        self._runTest(
            pss_spec_examples.spec_ex_154_pre_solve_post_solve,
            "154_pre_solve_post_solve.pss");

    #****************************************************************
    #* 156_post_solve_ordering_between_action_and_flow_objects.pss
    #****************************************************************
    def test_156_post_solve_ordering_between_action_and_flow_objects(self):
        self._runTest(
            pss_spec_examples.spec_ex_156_post_solve_ordering_between_action_and_flow_objects,
            "156_post_solve_ordering_between_action_and_flow_objects.pss");

    #****************************************************************
    #* 158_exec_body_block_sampling_external_data.pss
    #****************************************************************
    def test_158_exec_body_block_sampling_external_data(self):
        self._runTest(
            pss_spec_examples.spec_ex_158_exec_body_block_sampling_external_data,
            "158_exec_body_block_sampling_external_data.pss");

    #****************************************************************
    #* 160_generating_multiple_scenarios.pss
    #****************************************************************
    def test_160_generating_multiple_scenarios(self):
        self._runTest(
            pss_spec_examples.spec_ex_160_generating_multiple_scenarios,
            "160_generating_multiple_scenarios.pss");

    #****************************************************************
    #* 162_action_inferences_for_partially_specified_flows.pss
    #****************************************************************
    def test_162_action_inferences_for_partially_specified_flows(self):
        self._runTest(
            pss_spec_examples.spec_ex_162_action_inferences_for_partially_specified_flows,
            "162_action_inferences_for_partially_specified_flows.pss");

    #****************************************************************
    #* 164_object_pools_affect_inferencing.pss
    #****************************************************************
    def test_164_object_pools_affect_inferencing(self):
        self._runTest(
            pss_spec_examples.spec_ex_164_object_pools_affect_inferencing,
            "164_object_pools_affect_inferencing.pss");

    #****************************************************************
    #* 166_inline_data_constraints_affect_action_inferencing.pss
    #****************************************************************
    def test_166_inline_data_constraints_affect_action_inferencing(self):
        self._runTest(
            pss_spec_examples.spec_ex_166_inline_data_constraints_affect_action_inferencing,
            "166_inline_data_constraints_affect_action_inferencing.pss");

    #****************************************************************
    #* 168_data_constraints_affect_action_inferencing.pss
    #****************************************************************
    def test_168_data_constraints_affect_action_inferencing(self):
        self._runTest(
            pss_spec_examples.spec_ex_168_data_constraints_affect_action_inferencing,
            "168_data_constraints_affect_action_inferencing.pss");

    #****************************************************************
    #* 170_single_coverage_point.pss
    #****************************************************************
    def test_170_single_coverage_point(self):
        self._runTest(
            pss_spec_examples.spec_ex_170_single_coverage_point,
            "170_single_coverage_point.pss");

    #****************************************************************
    #* 172_two_coverage_points_and_cross_coverage_items.pss
    #****************************************************************
    def test_172_two_coverage_points_and_cross_coverage_items(self):
        self._runTest(
            pss_spec_examples.spec_ex_172_two_coverage_points_and_cross_coverage_items,
            "172_two_coverage_points_and_cross_coverage_items.pss");

    #****************************************************************
    #* 174_creating_a_covergroup_instance_with_a_formal_parameter_list.pss
    #****************************************************************
    def test_174_creating_a_covergroup_instance_with_a_formal_parameter_list(self):
        self._runTest(
            pss_spec_examples.spec_ex_174_creating_a_covergroup_instance_with_a_formal_parameter_list,
            "174_creating_a_covergroup_instance_with_a_formal_parameter_list.pss");

    #****************************************************************
    #* 176_creating_a_covergroup_instance_with_instance_options.pss
    #****************************************************************
    def test_176_creating_a_covergroup_instance_with_instance_options(self):
        self._runTest(
            pss_spec_examples.spec_ex_176_creating_a_covergroup_instance_with_instance_options,
            "176_creating_a_covergroup_instance_with_instance_options.pss");

    #****************************************************************
    #* 178_creating_an_inline_covergroup_instance.pss
    #****************************************************************
    def test_178_creating_an_inline_covergroup_instance(self):
        self._runTest(
            pss_spec_examples.spec_ex_178_creating_an_inline_covergroup_instance,
            "178_creating_an_inline_covergroup_instance.pss");

    #****************************************************************
    #* 180_specifying_an_iff_condition.pss
    #****************************************************************
    def test_180_specifying_an_iff_condition(self):
        self._runTest(
            pss_spec_examples.spec_ex_180_specifying_an_iff_condition,
            "180_specifying_an_iff_condition.pss");

    #****************************************************************
    #* 182_specifying_bins.pss
    #****************************************************************
    def test_182_specifying_bins(self):
        self._runTest(
            pss_spec_examples.spec_ex_182_specifying_bins,
            "182_specifying_bins.pss");

    #****************************************************************
    #* 184_select_all_values_from_0_to_255.pss
    #****************************************************************
    def test_184_select_all_values_from_0_to_255(self):
        self._runTest(
            pss_spec_examples.spec_ex_184_select_all_values_from_0_to_255,
            "184_select_all_values_from_0_to_255.pss");

    #****************************************************************
    #* 186_using_with_in_a_coverpoint.pss
    #****************************************************************
    def test_186_using_with_in_a_coverpoint(self):
        self._runTest(
            pss_spec_examples.spec_ex_186_using_with_in_a_coverpoint,
            "186_using_with_in_a_coverpoint.pss");

    #****************************************************************
    #* 188_excluding_coverage_point_values.pss
    #****************************************************************
    def test_188_excluding_coverage_point_values(self):
        self._runTest(
            pss_spec_examples.spec_ex_188_excluding_coverage_point_values,
            "188_excluding_coverage_point_values.pss");

    #****************************************************************
    #* 190_specifying_illegal_coverage_point_values.pss
    #****************************************************************
    def test_190_specifying_illegal_coverage_point_values(self):
        self._runTest(
            pss_spec_examples.spec_ex_190_specifying_illegal_coverage_point_values,
            "190_specifying_illegal_coverage_point_values.pss");

    #****************************************************************
    #* 192_value_resolution.pss
    #****************************************************************
    def test_192_value_resolution(self):
        self._runTest(
            pss_spec_examples.spec_ex_192_value_resolution,
            "192_value_resolution.pss");

    #****************************************************************
    #* 194_specifying_a_cross.pss
    #****************************************************************
    def test_194_specifying_a_cross(self):
        self._runTest(
            pss_spec_examples.spec_ex_194_specifying_a_cross,
            "194_specifying_a_cross.pss");

    #****************************************************************
    #* 196_specifying_cross_bins.pss
    #****************************************************************
    def test_196_specifying_cross_bins(self):
        self._runTest(
            pss_spec_examples.spec_ex_196_specifying_cross_bins,
            "196_specifying_cross_bins.pss");

    #****************************************************************
    #* 198_setting_options.pss
    #****************************************************************
    def test_198_setting_options(self):
        self._runTest(
            pss_spec_examples.spec_ex_198_setting_options,
            "198_setting_options.pss");

    #****************************************************************
    #* 200_per_instance_coverage_of_flow_objects.pss
    #****************************************************************
    def test_200_per_instance_coverage_of_flow_objects(self):
        self._runTest(
            pss_spec_examples.spec_ex_200_per_instance_coverage_of_flow_objects,
            "200_per_instance_coverage_of_flow_objects.pss");

    #****************************************************************
    #* 201_per_instance_coverage_in_actions.pss
    #****************************************************************
    def test_201_per_instance_coverage_in_actions(self):
        self._runTest(
            pss_spec_examples.spec_ex_201_per_instance_coverage_in_actions,
            "201_per_instance_coverage_in_actions.pss");

    #****************************************************************
    #* 202_type_extension.pss
    #****************************************************************
    def test_202_type_extension(self):
        self._runTest(
            pss_spec_examples.spec_ex_202_type_extension,
            "202_type_extension.pss");

    #****************************************************************
    #* 204_action_type_extension.pss
    #****************************************************************
    def test_204_action_type_extension(self):
        self._runTest(
            pss_spec_examples.spec_ex_204_action_type_extension,
            "204_action_type_extension.pss");

    #****************************************************************
    #* 206_enum_type_extensions.pss
    #****************************************************************
    def test_206_enum_type_extensions(self):
        self._runTest(
            pss_spec_examples.spec_ex_206_enum_type_extensions,
            "206_enum_type_extensions.pss");

    #****************************************************************
    #* 207_type_inheritance_and_overrides.pss
    #****************************************************************
    def test_207_type_inheritance_and_overrides(self):
        self._runTest(
            pss_spec_examples.spec_ex_207_type_inheritance_and_overrides,
            "207_type_inheritance_and_overrides.pss");

    #****************************************************************
    #* 210_data_instantiation_in_a_component.pss
    #****************************************************************
    def test_210_data_instantiation_in_a_component(self):
        self._runTest(
            pss_spec_examples.spec_ex_210_data_instantiation_in_a_component,
            "210_data_instantiation_in_a_component.pss");

    #****************************************************************
    #* 212_accessing_component_data_field_from_an_action.pss
    #****************************************************************
    def test_212_accessing_component_data_field_from_an_action(self):
        self._runTest(
            pss_spec_examples.spec_ex_212_accessing_component_data_field_from_an_action,
            "212_accessing_component_data_field_from_an_action.pss");

    #****************************************************************
    #* 214_referencing_pss_variables_using_mustache_notation.pss
    #****************************************************************
    def test_214_referencing_pss_variables_using_mustache_notation(self):
        self._runTest(
            pss_spec_examples.spec_ex_214_referencing_pss_variables_using_mustache_notation,
            "214_referencing_pss_variables_using_mustache_notation.pss");

    #****************************************************************
    #* 215_variable_reference_used_to_select_the_function.pss
    #****************************************************************
    def test_215_variable_reference_used_to_select_the_function(self):
        self._runTest(
            pss_spec_examples.spec_ex_215_variable_reference_used_to_select_the_function,
            "215_variable_reference_used_to_select_the_function.pss");

    #****************************************************************
    #* 216_declaring_a_random_func_id_variable_that_identifies_a_c_function_to_call.pss
    #****************************************************************
    def test_216_declaring_a_random_func_id_variable_that_identifies_a_c_function_to_call(self):
        self._runTest(
            pss_spec_examples.spec_ex_216_declaring_a_random_func_id_variable_that_identifies_a_c_function_to_call,
            "216_declaring_a_random_func_id_variable_that_identifies_a_c_function_to_call.pss");

    #****************************************************************
    #* 217_allowing_programmatic_declaration_of_a_target_variable_declaration.pss
    #****************************************************************
    def test_217_allowing_programmatic_declaration_of_a_target_variable_declaration(self):
        self._runTest(
            pss_spec_examples.spec_ex_217_allowing_programmatic_declaration_of_a_target_variable_declaration,
            "217_allowing_programmatic_declaration_of_a_target_variable_declaration.pss");

    #****************************************************************
    #* 218_pi_method.pss
    #****************************************************************
    def test_218_pi_method(self):
        self._runTest(
            pss_spec_examples.spec_ex_218_pi_method,
            "218_pi_method.pss");

    #****************************************************************
    #* 220_function_availability.pss
    #****************************************************************
    def test_220_function_availability(self):
        self._runTest(
            pss_spec_examples.spec_ex_220_function_availability,
            "220_function_availability.pss");

    #****************************************************************
    #* 222_explicit_specification_of_the_implementation_language.pss
    #****************************************************************
    def test_222_explicit_specification_of_the_implementation_language(self):
        self._runTest(
            pss_spec_examples.spec_ex_222_explicit_specification_of_the_implementation_language,
            "222_explicit_specification_of_the_implementation_language.pss");

    #****************************************************************
    #* 224_calling_pi_functions.pss
    #****************************************************************
    def test_224_calling_pi_functions(self):
        self._runTest(
            pss_spec_examples.spec_ex_224_calling_pi_functions,
            "224_calling_pi_functions.pss");

    #****************************************************************
    #* 226_reactive_control_flow.pss
    #****************************************************************
    def test_226_reactive_control_flow(self):
        self._runTest(
            pss_spec_examples.spec_ex_226_reactive_control_flow,
            "226_reactive_control_flow.pss");

    #****************************************************************
    #* 228_target_template_function_implementation.pss
    #****************************************************************
    def test_228_target_template_function_implementation(self):
        self._runTest(
            pss_spec_examples.spec_ex_228_target_template_function_implementation,
            "228_target_template_function_implementation.pss");

    #****************************************************************
    #* 230_import_class.pss
    #****************************************************************
    def test_230_import_class(self):
        self._runTest(
            pss_spec_examples.spec_ex_230_import_class,
            "230_import_class.pss");

    #****************************************************************
    #* 236_export_action.pss
    #****************************************************************
    def test_236_export_action(self):
        self._runTest(
            pss_spec_examples.spec_ex_236_export_action,
            "236_export_action.pss");

    #****************************************************************
    #* 240_conditional_processing_static_if.pss
    #****************************************************************
    def test_240_conditional_processing_static_if(self):
        self._runTest(
            pss_spec_examples.spec_ex_240_conditional_processing_static_if,
            "240_conditional_processing_static_if.pss");

    #****************************************************************
    #* 241_compile_has.pss
    #****************************************************************
    def test_241_compile_has(self):
        self._runTest(
            pss_spec_examples.spec_ex_241_compile_has,
            "241_compile_has.pss");

    #****************************************************************
    #* 242_circular_dependency.pss
    #****************************************************************
    def test_242_circular_dependency(self):
        self._runTest(
            pss_spec_examples.spec_ex_242_circular_dependency,
            "242_circular_dependency.pss");

    #****************************************************************
    #* 243_compile_assert.pss
    #****************************************************************
    def test_243_compile_assert(self):
        self._runTest(
            pss_spec_examples.spec_ex_243_compile_assert,
            "243_compile_assert.pss");

