
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

#********************************************************************
#* 003_enum_data_type.pss
#********************************************************************
spec_ex_003_enum_data_type='''

enum config_modes_e {UNKNOWN, MODE_A=10, MODE_B=20, MODE_C=35,
MODE_D=40};
component uart_c {
 action configure {
   rand config_modes_e mode;
   constraint {mode != UNKNOWN; }
 }
};
'''

#********************************************************************
#* 005_string_data_type.pss
#********************************************************************
spec_ex_005_string_data_type='''

struct string_s {
 rand bit a;
 rand string s;
 constraint {
 if (a == 1) {
 s == "FOO";
 } else {
 s == "BAR";
 }
 }
}
'''

#********************************************************************
#* 007_chandle_data_type.pss
#********************************************************************
spec_ex_007_chandle_data_type='''

function chandle do_init();
struct info_s {
 chandle ptr;

 exec pre_solve {
 ptr = do_init();
 }
}
'''

#********************************************************************
#* 008_struct_with_rand_modifier.pss
#********************************************************************
spec_ex_008_struct_with_rand_modifier='''

struct axi4_trans_req {
rand bit[31:0] axi_addr;
rand bit[31:0] axi_write_data;
rand bit is_write;
rand bit[3:0] prot;
rand bit[1:0] sema4;
}
'''

#********************************************************************
#* 010_typedef.pss
#********************************************************************
spec_ex_010_typedef='''

typedef bit[31:0] uint32_t;
'''

#********************************************************************
#* 012_fixed_size_arrays.pss
#********************************************************************
spec_ex_012_fixed_size_arrays='''

//<example>
struct S {
//</example>

int fixed_sized_arr [16]; // array of 16 signed integers
bit [7:0] byte_arr [256]; // array of 256 bytes
route east_routes [8]; // array of 8 route structs


//<example>
}
//</example>
'''

#********************************************************************
#* 014_sum_property_of_an_array.pss
#********************************************************************
spec_ex_014_sum_property_of_an_array='''

//<example>
struct S {
//</example>
	
bit [7:0] data [4];
 constraint data_c {
 data.sum > 0 && data.sum < 1000;
 }
 
//<example>
}
//</example>'''

#********************************************************************
#* 017_size_property_of_an_array.pss
#********************************************************************
spec_ex_017_size_property_of_an_array='''

//<example>
struct S {
//</example>

bit [7:0] data [4];
 constraint data_c {
 data.size < 10;
 }
 
//<example>
}
//</example>'''

#********************************************************************
#* 018_per_attribute_access_modifier.pss
#********************************************************************
spec_ex_018_per_attribute_access_modifier='''

struct S1 {
 rand int a; // public accessibility (default)
 private rand int b; // private accessibility
 rand int c; // public accessibility (default)
}
'''

#********************************************************************
#* 019_block_access_modifier.pss
#********************************************************************
spec_ex_019_block_access_modifier='''

struct S2 {
 private:
 rand int w; // private accessibility
 rand int x; // private accessibility
 public rand int y; // public accessibility
 rand int z; // private accessibility
 public:
 rand int s; // public accessibility
}
'''

#********************************************************************
#* 020_overlap_of_possible_enum_values.pss
#********************************************************************
spec_ex_020_overlap_of_possible_enum_values='''

//<example>
component top {
//</example>
	
enum config_modes_e {UNKNOWN, MODE_A=10, MODE_B=20};
enum foo_e {A=10, B, C};

action my_a {
 rand config_modes_e cfg;
 rand foo_e foo;
 constraint cfg == (config_modes_e)11; // illegal
 constraint cfg == (config_modes_e)foo; // cfg==MODE_A,
 // the only value in the numeric domain of both cfg and foo
 // ...
}

//<example>
}
//</example>'''

#********************************************************************
#* 021_casting_of_variable_to_a_vector.pss
#********************************************************************
spec_ex_021_casting_of_variable_to_a_vector='''

package external_fn_pkg {
 enum align_e {byte_aligned = 1, short_aligned = 2, word_aligned = 4};
 function bit[31:0] alloc_addr(bit[31:0] size, bit[3:0] align);
 buffer mem_seg_s {
 rand bit[31:0] size;
 bit[31:0] addr;
 align_e al;
 exec post_solve {
 addr = alloc_addr(size, (bit[3:0])al);
 }
 }
}
'''

#********************************************************************
#* 022_component.pss
#********************************************************************
spec_ex_022_component='''

component uart_c { /* ... */ };

'''

#********************************************************************
#* 024_namespace.pss
#********************************************************************
spec_ex_024_namespace='''

component usb_c {
 action write {/* ... */}
}
component uart_c {
 action write {/* ... */}
}
component pss_top {
 uart_c s1;
 usb_c s2;
 action entry {
 uart_c::write wr; //refers to the write action in uart_c
 // ...
 }
}
'''

#********************************************************************
#* 026_component_instantiation.pss
#********************************************************************
spec_ex_026_component_instantiation='''

component vid_pipe_c { /* ... */};
component codec_c {
 vid_pipe_c pipeA, pipeB;
 action decode { /* ... */};
};
component multimedia_ss_c {
 codec_c codecs[4];
};
component pss_top {
 multimedia_ss_c multimedia_ss;
};
'''

#********************************************************************
#* 028_constraining_a_comp_attribute.pss
#********************************************************************
spec_ex_028_constraining_a_comp_attribute='''

component vid_pipe_c { 
//<example>
 action program { /* ... */ }
//</example>
/* ... */ 
};

component codec_c {
 vid_pipe_c pipeA, pipeB;
 bit mode1_enable;

 
 action decode {
 	rand bit mode;
 
	constraint set_mode {
		comp.mode1_enable==0 -> mode == 0;
	}
	
	activity {
 		do vid_pipe_c::program with { comp == this.comp.pipeA; };
	}
 
  };
};

component multimedia_ss_c {
 codec_c codecs[2];
 exec init {
	codecs[0].mode1_enable = 0;
	codecs[1].mode1_enable = 1;
 };
};
'''

#********************************************************************
#* 030_atomic_action.pss
#********************************************************************
spec_ex_030_atomic_action='''

//<example>
component top {
buffer data_buf { /* ... */ }
//</example>
action write {
 output data_buf data;
 rand int size;
 // implementation details
 // ...
};


//<example>
}
//</example>
'''

#********************************************************************
#* 032_compound_action.pss
#********************************************************************
spec_ex_032_compound_action='''

//<example>
component top {
//</example>

action sub_a {/* ... */};
action compound_a {
 sub_a a1, a2;
 activity {
 a1;
 a2;
 }
}

//<example>
}
//</example>'''

#********************************************************************
#* 034_extended_action_traversal.pss
#********************************************************************
spec_ex_034_extended_action_traversal='''

component pss_top {
 action A { };
 action B { };
 action C { };
 action entry {
 activity {
 do A;
 }
 }
 extend action entry {
 activity {
 do B;
 }
 }
 extend action entry {
 activity {
 do C;
 }
 }
}

'''

#********************************************************************
#* 035_hand_coded_action_traversal.pss
#********************************************************************
spec_ex_035_hand_coded_action_traversal='''

component pss_top {
 action A { };
 action B { };
 action C { };
 action entry {
 activity {
 schedule {
 do A;
 do B;
 do C;
 }
 }
 }
}

'''

#********************************************************************
#* 036_inheritance_and_traversal.pss
#********************************************************************
spec_ex_036_inheritance_and_traversal='''

component pss_top {
 action A { }
 action B { }
 action C { }
 action base {
 activity {
 do A;
 }
 }
 action ext1 : base {
 activity {
 do B;
 }
 }
 action ext2 : base {
 activity {
 super;
 do C;
 }
 }
}


'''

#********************************************************************
#* 037_action_traversal.pss
#********************************************************************
spec_ex_037_action_traversal='''

//<example>
component top {
//</example>

action A {
 rand bit[3:0] f1;
 // ...
}
action B {
 A a1, a2;

 activity {
 a1;
 a2 with {
 f1 < 10;
 };
 }
}

//<example>
}
//</example>'''

#********************************************************************
#* 039_anonymous_action_traversal.pss
#********************************************************************
spec_ex_039_anonymous_action_traversal='''

//<example>
component top {
//</example>

action A {
 rand bit[3:0] f1;
 // ...
}
action B {
 activity {
 do A;
 do A with {f1 < 10;};
 }
}


//<example>
}
//</example>'''

#********************************************************************
#* 041_compound_action_traversal.pss
#********************************************************************
spec_ex_041_compound_action_traversal='''

// example
component top {
// example

action A {
 rand bit[3:0] f1;
 // ...
}
action B {
 A a1, a2;

 activity {
 a1;
 a2 with {
 f1 < 10;
 };
 }
}
action C {
 action bit[3:0] max;
 B b1;

 activity {
 	max;
	b1 with {
	 a1.f1 <= max;
 	};
 }
}

// example
}
// example

'''

#********************************************************************
#* 043_sequential_block.pss
#********************************************************************
spec_ex_043_sequential_block='''

// example
component top {
action A { /* ... */ }
action B { /* ... */ }
// example

action my_test {
 A a;
 B b;
 activity {
 a;
 b;
 }
};

// example
}
// example
'''

#********************************************************************
#* 045_variants_of_specifying_sequential_execution_in_activity.pss
#********************************************************************
spec_ex_045_variants_of_specifying_sequential_execution_in_activity='''

// example
component top {
// example

action my_test {
 A a;
 B b;
 activity {
 a;
 b;
 {a; b;};
 sequence{a; b;};
 }
};

// example
}
// example
'''

#********************************************************************
#* 047_parallel_statement.pss
#********************************************************************
spec_ex_047_parallel_statement='''

// example
component top {
 action A { /* ... */ }
 action B { /* ... */ }
 action C { /* ... */ }
// example

action my_test {
 A a;
 B b;
 C c;
 activity {
 a;
 parallel {
 b;
 c;
 }
 }
};

// example
}
// example
'''

#********************************************************************
#* 049_another_parallel_statement.pss
#********************************************************************
spec_ex_049_another_parallel_statement='''

// example
component top {
// example

resource R{ /* ... */}

pool [4] R R_pool;

bind R_pool *;

action A { lock R r; }
action B {}
action C {}
action D { lock R r;}
action my_test {
activity {
parallel {
{do A; do B;}
{do C; do D;}
}
}
}

// example
}
// example'''

#********************************************************************
#* 051_schedule_statement.pss
#********************************************************************
spec_ex_051_schedule_statement='''

// example
component top {
action A { /* ... */ }
action B { /* ... */ }
action C { /* ... */ }
// example

action my_test {
 A a;
 B b;
 C c;
 activity {
 a;
 schedule {
 b;
 c;
 }
 }
};

// example
}
// example
'''

#********************************************************************
#* 053_scheduling_block_with_sequential_sub_blocks.pss
#********************************************************************
spec_ex_053_scheduling_block_with_sequential_sub_blocks='''

// example
component top {
// example

action A {}
action B {}
action C {}
action D {}
action my_test {
activity {
schedule {
{do A; do B;}
{do C; do D;}
}
}
}


// example
}
// example'''

#********************************************************************
#* 055_repeat_statement.pss
#********************************************************************
spec_ex_055_repeat_statement='''

// example
component top {
 action A { /* ... */ }
 action B { /* ... */ }
// example

action my_test {
 A a;
 B b;
 activity {
 repeat (3) {
 a;
 b;
 }
 }
};

// example
}
// example
'''

#********************************************************************
#* 057_another_repeat_statement.pss
#********************************************************************
spec_ex_057_another_repeat_statement='''

// example
component top {
 action my_action1 { /* ... */ }
 action my_action2 { /* ... */ }
// example

action my_test {
 my_action1 action1;
 my_action2 action2;
 activity {
 repeat (i : 10) {
 if ((i % 4) == 0) {
 action1;
 } else {
 action2;
 }
 }
 }
};

// example
}
// example
'''

#********************************************************************
#* 059_repeat_while_statement.pss
#********************************************************************
spec_ex_059_repeat_while_statement='''

component top {
function bit is_last_one();
action do_something {
bit last_one;
exec post_solve {
last_one = comp.is_last_one();
}
exec body C = """
printf("Do Something\n");
""";
}
action entry {
do_something s1;
activity {
repeat {
s1;
} while (!s1.last_one);
}
}
}
'''

#********************************************************************
#* 061_foreach_statement.pss
#********************************************************************
spec_ex_061_foreach_statement='''

// example
component top {
// example

action my_action1 {
 rand bit in [0..3] val;
 // ...
}
action my_test {
 rand bit [4] in [0..3] a[16];
 my_action1 action1;

 activity {
 foreach (a[j]) {
 action1 with { action1.val <= a[j]; };
 }
 }
};

// example
}
// example
'''

#********************************************************************
#* 063_select_statement.pss
#********************************************************************
spec_ex_063_select_statement='''

// example
component top {
 action my_action1 { /* ... */ }
 action my_action2 { /* ... */ }
// example

action my_test {
 my_action1 action1;
 my_action2 action2;
 activity {
 select {
 action1;
 action2;
 }
 }
}

// example
}
// example
'''

#********************************************************************
#* 065_select_statement_with_guard_conditions_and_weights.pss
#********************************************************************
spec_ex_065_select_statement_with_guard_conditions_and_weights='''

// example
component top {
 action my_action1 { /* ... */ }
 action my_action2 { /* ... */ }
 action my_action3 { /* ... */ }
// example

action my_test {
my_action1 action1;
my_action2 action2;
my_action3 action3;
 rand int in [0..4] a;
 activity {
 select {
 (a == 0)[20]: action1;
 (a in [0..3])[30]: action2;
 [50]: action3;
 }
 }
}

// example
}
// example
'''

#********************************************************************
#* 067_if_else_statement.pss
#********************************************************************
spec_ex_067_if_else_statement='''

// example
component top {
 action A { /* ... */ }
 action B { /* ... */ }
// example

action my_test {
 rand int in [1..10] x;
 A a;
 B b;
 activity {
 if (x > 5)
 a;
 else
 b;
 }
};

// example
}
// example
'''

#********************************************************************
#* 069_match_statement.pss
#********************************************************************
spec_ex_069_match_statement='''

// <example>
component top {
  buffer security_data { /* ... */ }
  action my_action1 { /* ... */ }
  action my_action2 { /* ... */ }
  action my_action3 { /* ... */ }
// </example>

action my_test {
 input security_data in_security_data;
 my_action1 action1;
 my_action2 action2;
 my_action3 action3;
 activity {
 match (in_security_data.val) {
 	[LEVEL2..LEVEL4]: 
 		action1;
	[LEVEL3..LEVEL5]:
		action2;
	default:
		action3;
 }
}
}

// <example>
}
// </example>
'''

#********************************************************************
#* 071_using_a_symbol.pss
#********************************************************************
spec_ex_071_using_a_symbol='''

component entity {
action a { }
action b { }
action c { }
action top {
 a a1, a2, a3;
 b b1, b2, b3;
 c c1, c2, c3;
 symbol a_or_b {
 select {a1; b1; }
 select {a2; b2; }
 select {a3; b3; }
 }
 activity {
a_or_b;
 c1;
 c2;
 c3;
 }
}
}'''

#********************************************************************
#* 073_using_a_parameterized_symbol.pss
#********************************************************************
spec_ex_073_using_a_parameterized_symbol='''

component entity {
 action a { }
 action b { }
 action c { }
 action top {
 a a1, a2, a3;
 b b1, b2, b3;
 c c1, c2, c3;
 symbol ab_or_ba (a aa, b bb) {
 select {
 { aa; bb; }
 { bb; aa; }
 }
 }
 activity {
 ab_or_ba(a1,b1);
 ab_or_ba(a2,b2);
 ab_or_ba(a3,b3);
 c1;
 c2;
 c3;
 }
 }
}

'''

#********************************************************************
#* 075_scoping_and_named_sub_activities.pss
#********************************************************************
spec_ex_075_scoping_and_named_sub_activities='''

// example
component top {
// example

action A {};
action B {
 int x;
 activity {
 L1: parallel { // 'L1' is 1st level named sub-activity
 if (x > 10) {
 L2: { // 'L2' is 2nd level named sub-activity
 A a;
 a;
 }
 {
 A a; // OK - this is a separate naming scope for variables
 a;
 }
 }
 L2: { // Error - this 'L2' conflicts with 'L2' above
 A a;
 a;
 }
 }
 }
};

// example
}
// example

'''

#********************************************************************
#* 076_hierarchical_references_and_named_subactivities.pss
#********************************************************************
spec_ex_076_hierarchical_references_and_named_subactivities='''

//<example>
component top {
//</example>

action A { rand int x; };
action B {
 A a;
 activity {
 a;
 my_seq: sequence {
 A a;
 a;
 parallel {
	 my_rep: repeat (3) {
	 	A a;
	 	a;
	 };
	 
	 sequence { A a; a; }; // this 'a' is declared in unnamed scope
	 A a; // can't be accessed from outside
	a;
 };
};
};
};
 
action C {
 B b1, b2;
 constraint b1.a.x == 1;
 constraint b1.my_seq.a.x == 2;
 constraint b1.my_seq.my_rep.a.x == 3; // applies to all three iterations
 // of the loop
 activity {
 b1;
 b2 with { my_seq.my_rep.a.x == 4; }; // likewise
 }
};

//<example>
}
//</example>
'''

#********************************************************************
#* 077_bind_statement.pss
#********************************************************************
spec_ex_077_bind_statement='''

component top{
 buffer B {int a;};
 action P1 {
   output B out;
 };
 action P2 {
   output B out;
 };
 action C {
   input B inp;
 };

 pool B B_p;
 bind B {*};

 action T {
   P1 p1;
   P2 p2;
   C c;
   activity {
     p1; 
     p2; 
     c;
     bind p1.out c.inp;
   };
 }
};

'''

#********************************************************************
#* 079_hierarchical_flow_binding.pss
#********************************************************************
spec_ex_079_hierarchical_flow_binding='''

// example
component top {
 buffer data_buf { /* ... */ }
// example

action sub_a {
 input data_buf din;
 output data_buf dout;
}
action compound_a {
 input data_buf data_in;
 output data_buf data_out;
 sub_a a1, a2;
 activity {
 a1;
 a2;
 bind a1.dout a2.din;
 bind data_in a1.din;
 bind data_out a2.dout;
 }
}

// example
}
// example
'''

#********************************************************************
#* 081_hierarchical_resource_binding.pss
#********************************************************************
spec_ex_081_hierarchical_resource_binding='''

// example
component top {
  resource reslk_r { /* ... */ }
  resource resshr_r { /* ... */ }
// example

action sub_a {
 lock reslk_r rlkA, rlkB;
 share resshr_r rshA, rshB;
}

action compound_a {
 lock reslk_r crlkA, crlkB;
 share resshr_r crshA, crshB;
 sub_a a1, a2;
 activity {
 schedule {
 a1;
 a2;
 }
 bind crlkA {a1.rlkA, a2.rlkA};
 bind crshA {a1.rshA, a2.rshA};
 bind crlkB {a1.rlkB, a2.rshB};
 bind crshB {a1.rshB, a2.rlkB}; //illegal
 }
}

// example
}
// example
'''

#********************************************************************
#* 083_buffer_object.pss
#********************************************************************
spec_ex_083_buffer_object='''

struct mem_segment_s {/* ... */};

buffer data_buff_s {
 rand mem_segment_s seg;
};
'''

#********************************************************************
#* 085_stream_object.pss
#********************************************************************
spec_ex_085_stream_object='''

struct mem_segment_s { /* ... */};
stream data_stream_s {
 rand mem_segment_s seg;
 };
 '''

#********************************************************************
#* 087_state_object.pss
#********************************************************************
spec_ex_087_state_object='''

enum mode_e { /* ... */ };
state config_s {
 rand mode_e mode;
 /* ... */
};
'''

#********************************************************************
#* 089_buffer_flow_object.pss
#********************************************************************
spec_ex_089_buffer_flow_object='''

// example
component top {
// example

struct mem_segment_s {/*... */};
buffer data_buff_s {
 rand mem_segment_s seg;
 };
action cons_mem_a {
 input data_buff_s in_data;
};
action prod_mem_a {
 output data_buff_s out_data;
};

// example
}
// example
'''

#********************************************************************
#* 091_stream_flow_object.pss
#********************************************************************
spec_ex_091_stream_flow_object='''

// example
component top {
// example

struct mem_segment_s {/* ... */};
stream data_stream_s {
 rand mem_segment_s seg;
 };
action cons_mem_a {
 input data_stream_s in_data;
};
action prod_mem_a {
 output data_stream_s out_data;
};

// example
}
// example
'''

#********************************************************************
#* 093_declaring_a_resource.pss
#********************************************************************
spec_ex_093_declaring_a_resource='''

resource DMA_channel_s {
 rand bit[3:0] priority;
};
'''

#********************************************************************
#* 095_resource_object.pss
#********************************************************************
spec_ex_095_resource_object='''

//<example>
component top {
//</example>
resource DMA_channel_s {
 rand bit[3:0] priority;
};

resource CPU_core_s { /* ... */ };
action two_chan_transfer {
 lock DMA_channel_s chan_A;
 lock DMA_channel_s chan_B;
 share CPU_core_s ctrl_core;
 /* ... */
};

//<example>
}
//</example>'''

#********************************************************************
#* 097_pool_declaration.pss
#********************************************************************
spec_ex_097_pool_declaration='''

//<example>
struct mem_segment_s { /* ... */ }
//</example>

buffer data_buff_s {
 rand mem_segment_s seg;
 };
 
resource channel_s { /*...*/ };
component dmac_c {
 pool data_buff_s buff_p;
 // ...
 pool [4] channel_s chan_p;
}
'''

#********************************************************************
#* 099_static_binding.pss
#********************************************************************
spec_ex_099_static_binding='''

struct mem_segment_s { /* ... */ };
buffer data_buff_s {
 rand mem_segment_s seg;
 };
resource channel_s {/* ... */ };
component dma_sub_c {
 /* ... */
}
component dmac_c {
 dma_sub_c dmas1, dmas2;
 pool data_buff_s buff_p;
 bind buff_p {*};
 pool [4] channel_s chan_p;
 bind chan_p {dmas1.*, dmas2.*};
 action mem2mem_a {
 input data_buff_s in_data;
 output data_buff_s out_data;
 /* ... */
 }
}

'''

#********************************************************************
#* 101_pool_binding.pss
#********************************************************************
spec_ex_101_pool_binding='''

state power_state_s { rand int in [0..4] level; }
resource channel_s {}
component graphics_c {
 pool power_state_s power_state_var;
 bind power_state_var *; // accessible to all actions under this
 // component (specifically power_transition's
 //input/output)
 action power_transition {
 input power_state_s curr; //current state
 output power_state_s next; //next state
 lock channel_s chan;
 }
}
component my_multimedia_ss_c {
 graphics_c gfx0;
 graphics_c gfx1;
 pool [4] channel_s channels;
 bind channels {gfx0.*,gfx1.*};// accessible by default to all
 // actions under these components sub-tree
 // (specifically power_transition's chan)
 action observe_same_power_state {
 input power_state_s gfx0_state;
 input power_state_s gfx1_state;
 constraint gfx0_state.level == gfx1_state.level;
 }
 // explicit binding of the two power state variables to the
 // respective inputs of action observe_same_power_state
 bind gfx0.power_state_var observe_same_power_state.gfx0_state;
 bind gfx1.power_state_var observe_same_power_state.gfx1_state;
}

'''

#********************************************************************
#* 103_resource_object_assignment.pss
#********************************************************************
spec_ex_103_resource_object_assignment='''

resource cpu_core_s {}
component dma_c {
 resource channel_s {}
 pool[2] channel_s channels;
 bind channels {*}; // accessible to all actions
 // under this component (and its sub-tree)
 action transfer {
 lock channel_s chan;
 lock cpu_core_s core;
 }
}
component pss_top {
 dma_c dma0,dma1;
 pool[4] cpu_core_s cpu;
 bind cpu {dma0.*, dma1.*};// accessible to all actions
 // under the two sub-components
 action par_dma_xfers {
 dma_c::transfer xfer_a;
 dma_c::transfer xfer_b;
  // ...
 constraint {xfer_a.core.instance_id != xfer_b.core.instance_id;};
 constraint {xfer_a.chan.instance_id == xfer_b.chan.instance_id;};
 }
}

'''

#********************************************************************
#* 105_state_object_binding.pss
#********************************************************************
spec_ex_105_state_object_binding='''

enum codec_config_mode_e {UNKNOWN, A, B}
component codec_c {
 state configuration_s {
 rand codec_config_mode_e mode;
 constraint initial -> mode == UNKNOWN;
 }
 pool configuration_s config_var;
 bind config_var *;
 action configure {
 input configuration_s prev_conf;
 output configuration_s next_conf;
 constraint prev_conf.mode == UNKNOWN && next_conf.mode in [A, B];
 }
}

'''

#********************************************************************
#* 107_declaring_a_static_constraint.pss
#********************************************************************
spec_ex_107_declaring_a_static_constraint='''

//<example>
component top {
//</example>

action A {
 rand bit[31:0] addr;

 constraint addr_c {
 addr == 0x1000;
 }
}

//<example>
}
//</example>'''

#********************************************************************
#* 109_declaring_a_dynamic_constraint.pss
#********************************************************************
spec_ex_109_declaring_a_dynamic_constraint='''

//<example>
component top {
//</example>

action B {
 action bit[31:0] addr;

 dynamic constraint dyn_addr1_c {
 addr in [0x1000..0x1FFF];
 }

 dynamic constraint dyn_addr2_c {
 addr in [0x2000..0x2FFF];
 }
}

//<example>
}
//</example>
'''

#********************************************************************
#* 111_declaring_a_dynamic_constraint_inside_a_static_constraint.pss
#********************************************************************
spec_ex_111_declaring_a_dynamic_constraint_inside_a_static_constraint='''

//<example>
component top {
//</example>

 action send_pkt {
 rand bit[15:0] pkt_sz;
 constraint pkt_sz_c { pkt_sz > 0; }
 constraint interesting_sz_c { small_pkt_c || jumbo_pkt_c; }
 dynamic constraint small_pkt_c { pkt_sz >= 100; }
 dynamic constraint jumbo_pkt_c {pkt_sz > 1500; }
 }
 action scenario {
 activity {
 do send_pkt; // Send a packet with size in [1..100, 1500..65535]
 do send_pkt with {pkt_sz >= 100; }; // Send a small packet with
 // a directly-specified inline constraint
 do send_pkt with {small_pkt_c; }; // Send a small packet by
 // referencing a dynamic constraint
 }
 }
 
//<example>
}
//</example>'''

#********************************************************************
#* 113_inheriting_and_overriding_constraints.pss
#********************************************************************
spec_ex_113_inheriting_and_overriding_constraints='''

buffer data_buff {
rand int size;
constraint size in [1..1024];
constraint size_align { size%4 == 0; } // 4 byte aligned
}
buffer corrupt_data_buff : data_buff {
constraint size_align { size%4 == 1; }
//overrides alignment 1 byte off
constraint corrupt_data_size { size > 256; }
// additional constraint
}
'''

#********************************************************************
#* 115_action_traversal_in_line_constraint.pss
#********************************************************************
spec_ex_115_action_traversal_in_line_constraint='''

//<example>
component top {
//</example>

action A {
 rand bit[3:0] f;
};
action B {
 A a1, a2, a3, a4;

 constraint c1 { a1.f in [8..15]; };
 constraint c2 { a1.f == a4.f; };
 activity {
 a1;
 a2 with {
 f in [8..15]; // same effect as constraint c1 has on a1
 };
 a3 with {
 f == a4.f; // illegal - a4.f is unresolved at this point
 };
 a4;
 }
};

//<example>
}
//</example>
'''

#********************************************************************
#* 117_variable_resolution_inside_with_constraint_block.pss
#********************************************************************
spec_ex_117_variable_resolution_inside_with_constraint_block='''
component subc {
action A {
rand int f;
rand int g;
}
}
component top {
subc sub1, sub2;
action B {
rand int f;
rand int h;
subc::A a;
activity {
a with {
f < h; // sub-action's f and containing action's h
g == this.f; // sub-action's g and containing action's f
comp == this.comp.sub1; // sub-action's component is
// sub-component 'sub1' of the
// parent action's component
};
}
}
}
'''

#********************************************************************
#* 119_in_constraint.pss
#********************************************************************
spec_ex_119_in_constraint='''

//<example>
struct S {
 rand bit[32] addr;
//</example>
constraint addr_c {
 addr in [0x0000..0xFFFF];
 }
 
//<example>
}
//</example>
'''

#********************************************************************
#* 121_implication_constraint.pss
#********************************************************************
spec_ex_121_implication_constraint='''

struct impl_s {
 rand bit[7:0] a, b;

 constraint ab_c {
 (a > 5) -> b == 1;
 }
}
'''

#********************************************************************
#* 123_if_constraint.pss
#********************************************************************
spec_ex_123_if_constraint='''
struct if_else_s {
 rand bit[7:0] a, b;

 constraint ab_c {
 if (a > 5) {
 b == 1;
 } else {
 b < a;
 }
 }
}
'''

#********************************************************************
#* 125_foreach_iterative_constraint.pss
#********************************************************************
spec_ex_125_foreach_iterative_constraint='''

struct foreach_s {
 rand bit[9:0] fixed_arr[10];

 constraint fill_arr_elem_c {
 foreach (fixed_arr[i]) {
 if (i > 0) {
 fixed_arr[i] > fixed_arr[i-1];
 }
 }
 }
}
'''

#********************************************************************
#* 127_unique_constraint.pss
#********************************************************************
spec_ex_127_unique_constraint='''

struct my_struct {
rand bit[4] in [0..15] A, B, C;
constraint unique_abc_c {
unique {A, B, C};
}
}
'''

#********************************************************************
#* 129_scheduling_constraints.pss
#********************************************************************
spec_ex_129_scheduling_constraints='''

//<example>
component top {
//</example>

action my_sub_flow {
 A a; B b; C c; D d;
 activity {
 sequence {
 a;
 schedule {
 b; c; d;
 };
 };
 };
};
action my_top_flow {
 my_sub_flow sf1, sf2;
 activity {
 schedule {
 sf1;
 sf2;
 };
 };
 constraint sequence {sf1.a, sf2.b};
 constraint parallel {sf1.b, sf2.b, sf2.d};
};

//<example>
}
//</example>
'''

#********************************************************************
#* 130_sequencing_constraint.pss
#********************************************************************
spec_ex_130_sequencing_constraint='''

state power_state_s {
 rand int in [0..3] domain_A, domain_B, domain_C;
 constraint domain_B in [ prev.domain_B - 1,
 prev.domain_B,
 prev.domain_B + 1];
 constraint prev.domain_C==0 -> domain_C in[0,1] || domain_B==0;
};
//...
component power_ctrl_c {
 pool power_state_s psvar;
 bind psvar *;
 action power_trans1 {
 output power_state_s next_state;
 };
 action power_trans2 {
 output power_state_s next_state;
 constraint next_state.domain_C == 0;
 };
};

'''

#********************************************************************
#* 132_struct_rand_and_non_rand_fields.pss
#********************************************************************
spec_ex_132_struct_rand_and_non_rand_fields='''

struct S1 {
 rand bit[3:0] a;
 bit[3:0] b;
}
struct S2 {
 rand S1 s1_1;
 S1 s1_2;
}
'''

#********************************************************************
#* 134_action_rand_qualified_fields.pss
#********************************************************************
spec_ex_134_action_rand_qualified_fields='''

//<example>
component top {
//</example>

action A {
 rand bit[3:0] a;
 }

 action B {
 A a_1, a_2;
 rand bit[3:0] b;

 activity {
 a_1;
 a_2;
 }
 }

//<example>
}
//</example>
 '''

#********************************************************************
#* 136_action_qualified_data_fields.pss
#********************************************************************
spec_ex_136_action_qualified_data_fields='''


//<example>
component top {
//</example>

action A {
 rand bit[3:0] a;
 }

 action B {
 action bit[3:0] a_bit;
 A a_1;

 activity {
 a_bit;
 a_1;
 }
 }
 
//<example>
}
//</example>'''

#********************************************************************
#* 138_randomizing_flow_object_attributes.pss
#********************************************************************
spec_ex_138_randomizing_flow_object_attributes='''

component top {
buffer mem_obj {
int dat;
constraint dat%2 == 0; // dat must be even
}
action write1 {
output mem_obj out_obj;
constraint out_obj.dat in [1..5];
}
action write2 {
output mem_obj out_obj;
constraint out_obj.dat in [6..10];
}
action read {
input mem_obj in_obj;
constraint in_obj.dat in [8..12];
}
action test {
activity {
do write1;
do read;
}
}
}

'''

#********************************************************************
#* 140_randomizing_resource_object_attributes.pss
#********************************************************************
spec_ex_140_randomizing_resource_object_attributes='''

component top {
enum rsrc_kind_e {A, B, C, D};
resource rsrc_obj {
rand rsrc_kind_e kind;
}
pool[2] rsrc_obj rsrc_pool;
bind rsrc_pool *;
action something {
share rsrc_obj my_rsrc_inst;
constraint my_rsrc_inst.kind != A;
}
action something_else {
lock rsrc_obj my_rsrc_inst;
}
action test {
activity {
parallel {
do something with { my_rsrc_inst.kind != B; };
 do something with { my_rsrc_inst.kind != C; };
 do something_else;
}
}
}
}

'''

#********************************************************************
#* 142_activity_with_random_fields.pss
#********************************************************************
spec_ex_142_activity_with_random_fields='''


//<example>
component top {
//</example>

action A {
 rand bit[3:0] val;
}

action my_action {
 A a, b, c;
 constraint abc_c {
 a.val < b.val;
 b.val < c.val;
 }
 activity {
 a;
 b;
 c;
 }
}

//<example>
}
//</example>
'''

#********************************************************************
#* 144_activity_with_random_fields_in_a_loop.pss
#********************************************************************
spec_ex_144_activity_with_random_fields_in_a_loop='''

//<example>
component top {
//</example>

action A {
 rand bit[3:0] val;
}

action my_action {
 A a, b, c, d;
 constraint abc_c {
 a.val < b.val;
 b.val < c.val;
 c.val < d.val;
 }
 activity {
 a;
 repeat (2) {
 b;
 c;
 d;
 }
 }
}

//<example>
}
//</example>
'''

#********************************************************************
#* 146_struct_with_random_fields.pss
#********************************************************************
spec_ex_146_struct_with_random_fields='''

struct abc_s {
rand bit[4] in [0..15] a_val, b_val, c_val;
constraint {
a_val < b_val;
b_val < c_val;
}
}
'''

#********************************************************************
#* 148_activity_with_random_fields.pss
#********************************************************************
spec_ex_148_activity_with_random_fields='''


//<example>
component top {
//</example>

action A {
 rand bit[3:0] val;
}

action my_action {
 A a, b, c;
 constraint abc_c {
 a.val < b.val;
 b.val < c.val;
 }
 activity {
 a;
 b;
 c;
 }
}

//<example>
}
//</example>
'''

#********************************************************************
#* 150_sub_activity_traversal.pss
#********************************************************************
spec_ex_150_sub_activity_traversal='''

component top {
action A {
rand bit[3:0] val;
}
action sub {
A a, b, c;
constraint abc_c {
a.val < b.val;
b.val < c.val;
}
activity {
a;
b;
c;
}
}
action top_action {
A v;
sub s1;
constraint c {
s1.a.val == v.val;
}
activity {
v;
s1;
}
}
}
'''

#********************************************************************
#* 152_activity_with_dynamic_constraints.pss
#********************************************************************
spec_ex_152_activity_with_dynamic_constraints='''

//<example>
component top {
//</example>

action A {
 rand bit[3:0] val;
}
action dyn {
 A a, b;

 dynamic constraint d1 {
 b.val < a.val;
 b.val <= 5;
 }

 dynamic constraint d2 {
 b.val > a.val;
 b.val <= 7;
 }

 activity {
 a;
 select {
 d1;
 d2;
 }
 b;
 }
}

//<example>
}
//</example>
'''

#********************************************************************
#* 154_pre_solve_post_solve.pss
#********************************************************************
spec_ex_154_pre_solve_post_solve='''

function bit[5:0] get_init_val();
function bit[5:0] get_exp_val(bit[5:0] stim_val);
struct S1 {
bit[5:0] init_val;
rand bit[5:0] rand_val;
bit[5:0] exp_val;
exec pre_solve {
init_val = get_init_val();
}
constraint rand_val_c {
rand_val <= init_val+10;
}
exec post_solve {
exp_val = get_exp_val(rand_val);
}
}
struct S2 {
bit[5:0] init_val;
rand bit[5:0] rand_val;
bit[5:0] exp_val;
rand S1 s1_1, s1_2;
exec pre_solve {
init_val = get_init_val();
}
constraint rand_val_c {
rand_val > init_val;
}
exec post_solve {
exp_val = get_exp_val(rand_val);
}
}
'''

#********************************************************************
#* 156_post_solve_ordering_between_action_and_flow_objects.pss
#********************************************************************
spec_ex_156_post_solve_ordering_between_action_and_flow_objects='''


//<example>
component top {
//</example>

buffer mem_obj {
 exec post_solve { /* ... */}
};
action write {
 output mem_obj out_obj;
 exec post_solve { /* ... */ }
};
action read {
 input mem_obj in_obj;
 exec post_solve { /* ... */ }
};
action test {
 write wr;
 read rd;
 activity {
 	wr;
 	rd;
	bind wr.out_obj rd.in_obj;
 }
 exec post_solve { /* ... */ }
};

//<example>
}
//</example>'''

#********************************************************************
#* 158_exec_body_block_sampling_external_data.pss
#********************************************************************
spec_ex_158_exec_body_block_sampling_external_data='''

function bit[3:0] compute_val1(bit[3:0] v);
function bit[3:0] compute_val2(bit[3:0] v);
component pss_top {

 action A {
 rand bit[3:0] x;
 bit[3:0] y1, y2;

 constraint assume_y_c {
 y1 >= x && y1 <= x+2;
 y2 >= x && y2 <= x+3;

 y1 <= y2;
 }

 exec body {
 y1 = compute_val1(x);
 y2 = compute_val2(x);
 }
 }
}
'''

#********************************************************************
#* 160_generating_multiple_scenarios.pss
#********************************************************************
spec_ex_160_generating_multiple_scenarios='''

component pss_top {
 buffer data_buff_s {
 rand int val;};
 pool data_buff_s data_mem;
 bind data_mem *;
 action A_a {output data_buff_s dout;};
 action B_a {output data_buff_s dout;};
 action C_a {input data_buff_s din;};
 action D_a {input data_buff_s din;};
 action root_a {
 A_a a;
 B_a b;
 C_a c;
 D_a d;
 activity {
 select {a; b;}
 select {c; d;}
 }
 }
}

'''

#********************************************************************
#* 162_action_inferences_for_partially_specified_flows.pss
#********************************************************************
spec_ex_162_action_inferences_for_partially_specified_flows='''

component pss_top {
 state config_s {};
 pool config_s config_var;
 bind config_var *;
 buffer data_buff_s {};
 pool data_buff_s data_mem;
 bind data_mem *;
 stream data_stream_s {};
 pool data_stream_s data_bus;
 bind data_bus *;
 action setup_A {
 output config_s new_cfg;
 };
 action setup_B {
 output config_s new_cfg;
 };
 action load_data {
 input config_s curr_cfg;
 constraint !curr_cfg.initial;
 output data_buff_s out_data;
 };
 action send_data {
 input data_buff_s src_data;
 output data_stream_s out_data;
 };
 action receive_data {
 input data_stream_s in_data;
 };
};

'''

#********************************************************************
#* 164_object_pools_affect_inferencing.pss
#********************************************************************
spec_ex_164_object_pools_affect_inferencing='''

component pss_top {
 buffer data_buff_s {/* ... */};
 // Note: PSS 1.0 only allows one pool per declaration
 pool data_buff_s data_mem1;
 pool data_buff_s data_mem2;
 bind data_mem1 {A_a.dout, C_a.din};
 bind data_mem2 {B_a.dout, D_a.din};
 action A_a {output data_buff_s dout;};
 action B_a {output data_buff_s dout;};
 action C_a {input data_buff_s din;};
 action D_a {input data_buff_s din;};
 action root_a {
 C_a c;
 D_a d;
 activity {
 select {c; d;}
 }
 }
}

'''

#********************************************************************
#* 166_inline_data_constraints_affect_action_inferencing.pss
#********************************************************************
spec_ex_166_inline_data_constraints_affect_action_inferencing='''
component pss_top {
 buffer data_buff_s {
 rand int val;};
 pool data_buff_s data_mem;
 bind data_mem *;
 action A_a {output data_buff_s dout;};
 action B_a {output data_buff_s dout;};
 action C_a {input data_buff_s din;};
 action D_a {input data_buff_s din;};
 action root_a {
 A_a a;
 B_a b;
 C_a c;
 D_a d;
 activity {
 select {a with{dout.val<5;}; b with {dout.val<5;};}
 select {c; d with {din.val>5;};}
 }
 }
}

'''

#********************************************************************
#* 168_data_constraints_affect_action_inferencing.pss
#********************************************************************
spec_ex_168_data_constraints_affect_action_inferencing='''
component pss_top {
 buffer data_buff_s {
 rand int val;};
 pool data_buff_s data_mem;
 bind data_mem *;
 action A_a {
 output data_buff_s dout;
 constraint {dout.val<5;}
 };
 action B_a {
 output data_buff_s dout;
 constraint {dout.val<5;}
 };
 action C_a {input data_buff_s din;};
 action D_a {
 input data_buff_s din;
 constraint {din.val > 5;}
 };
 action root_a {
 A_a a;
 B_a b;
 C_a c;
 D_a d;
 activity {
 select {a; b;}
 select {c; d;}
 }
 }
}

'''

#********************************************************************
#* 170_single_coverage_point.pss
#********************************************************************
spec_ex_170_single_coverage_point='''
enum color_e {red, green, blue};
struct s {
rand color_e color;
covergroup {
c : coverpoint color;
} cs1;
}
'''

#********************************************************************
#* 172_two_coverage_points_and_cross_coverage_items.pss
#********************************************************************
spec_ex_172_two_coverage_points_and_cross_coverage_items='''

enum color_e {red, green, blue};
struct s {
 rand color_e color;
 rand bit[3:0] pixel_adr, pixel_offset, pixel_hue;
 covergroup {
 Hue : coverpoint pixel_hue;
 Offset : coverpoint pixel_offset;
 AxC: cross color, pixel_adr;
 all : cross color, Hue, Offset;
 } cs2;
}

'''

#********************************************************************
#* 174_creating_a_covergroup_instance_with_a_formal_parameter_list.pss
#********************************************************************
spec_ex_174_creating_a_covergroup_instance_with_a_formal_parameter_list='''

enum color_e {red, green, blue};
struct s {
rand color_e color;
covergroup cs1(color_e c) {
c : coverpoint c;
}
cs1 cs1_inst(color);
}
'''

#********************************************************************
#* 176_creating_a_covergroup_instance_with_instance_options.pss
#********************************************************************
spec_ex_176_creating_a_covergroup_instance_with_instance_options='''

enum color_e {red, green, blue};

struct s {
	rand color_e color;
	
	covergroup cs1 (color_e color) {
		c : coverpoint color;
	}
	
	cs1 cs1_inst(color) with {
		option.at_least = 2;
	};
}
'''

#********************************************************************
#* 178_creating_an_inline_covergroup_instance.pss
#********************************************************************
spec_ex_178_creating_an_inline_covergroup_instance='''

enum color_e {red, green, blue};
struct s {
rand color_e color;
covergroup {
option.at_least = 2;
c : coverpoint color;
} cs1_inst;
}
'''

#********************************************************************
#* 180_specifying_an_iff_condition.pss
#********************************************************************
spec_ex_180_specifying_an_iff_condition='''

struct s {
rand bit[3:0] s0;
rand bit is_s0_enabled;
covergroup {
coverpoint s0 iff (is_s0_enabled);
} cs4;
}
'''

#********************************************************************
#* 182_specifying_bins.pss
#********************************************************************
spec_ex_182_specifying_bins='''

struct s {
	rand bit[10] v_a;
	
	covergroup {
		coverpoint v_a {
			bins a = [0..63, 65];
			bins b[] = [127..150, 148..191];
			bins c[] = [200, 201, 202];
			bins d = [1000..];
			bins others[] = default;
		}
	} cs;
}
'''

#********************************************************************
#* 184_select_all_values_from_0_to_255.pss
#********************************************************************
spec_ex_184_select_all_values_from_0_to_255='''

struct s {
rand bit[8] x;
covergroup {
a: coverpoint x {
bins mod3[] = [0..255] with (item % 3 == 0);
}
} cs;
}
'''

#********************************************************************
#* 186_using_with_in_a_coverpoint.pss
#********************************************************************
spec_ex_186_using_with_in_a_coverpoint='''

struct s {
	rand bit[8] x;
	
	covergroup {
		a: coverpoint x {
		bins mod3[] = a with ((a % 3) == 0);
		}
	} cs;
}
'''

#********************************************************************
#* 188_excluding_coverage_point_values.pss
#********************************************************************
spec_ex_188_excluding_coverage_point_values='''

struct s {
  rand bit[4] a;

  covergroup {
    a_cp: coverpoint a {
      ignore_bins ignore_vals = [7,8];
    }
  } cs;
}

'''

#********************************************************************
#* 190_specifying_illegal_coverage_point_values.pss
#********************************************************************
spec_ex_190_specifying_illegal_coverage_point_values='''

struct s {
rand bit[4] a;
covergroup {
coverpoint a {
illegal_bins illegal_vals = [7, 8];
}
} cs23;
}
'''

#********************************************************************
#* 192_value_resolution.pss
#********************************************************************
spec_ex_192_value_resolution='''

struct s {
	rand bit[3] p1;
	int [3] p2;
	
	covergroup {
		coverpoint p1 {
			bins b1 = [1, 2..5, 6..10];
			bins b2 = [-1, 1..10, 15];
		}
		coverpoint p2 {
			bins b3 = [1, 2..5, 6..10];
			bins b4 = [-1, 1..10, 15];
		}
	} c1;
}
'''

#********************************************************************
#* 194_specifying_a_cross.pss
#********************************************************************
spec_ex_194_specifying_a_cross='''

struct s {
rand bit[4] a, b;
covergroup {
aXb : cross a, b;
} cov;
}
'''

#********************************************************************
#* 196_specifying_cross_bins.pss
#********************************************************************
spec_ex_196_specifying_cross_bins='''

struct s {
rand bit[4] a, b;
covergroup {
coverpoint a {
bins low[] = [0..127];
bins high = [128..255];
}
coverpoint b {
bins two[] = b with (b%2 == 0);
}
X : cross a, b {
bins small_a_b = X with (a <= 10 && b<=10);
}
} cov;
}
'''

#********************************************************************
#* 198_setting_options.pss
#********************************************************************
spec_ex_198_setting_options='''

covergroup cs1 (bit[64] a_var, bit[64] b_var) {
option.per_instance = 1;
option.comment = "This is CS1";
a : coverpoint a_var {
option.auto_bin_max = 128;
}
b : coverpoint b_var {
option.weight = 10;
}
}
'''

#********************************************************************
#* 200_per_instance_coverage_of_flow_objects.pss
#********************************************************************
spec_ex_200_per_instance_coverage_of_flow_objects='''

enum mode_e { M0, M1, M2 }
buffer b1 {
rand mode_e mode;
covergroup {
option.per_instance = true;
coverpoint mode;
} cs;
}
component pss_top {
pool b1 b1_p;
bind b1_p *;
action P_a {
output b1 b1_out;
}
action C_a {
input b1 b1_in;
}
action entry {
activity {
repeat (10) {
do C_a;
}
}
}
}

'''

#********************************************************************
#* 201_per_instance_coverage_in_actions.pss
#********************************************************************
spec_ex_201_per_instance_coverage_in_actions='''

enum mode_e { M0, M1, M2 }
component pss_top {
action A {
rand mode_e mode;
covergroup {
option.per_instance = true;
coverpoint mode;
} cg;
}
action entry {
A a1;
activity {
repeat (4) {
a1;
}
repeat (10) {
do A;
}
}
}
}

'''

#********************************************************************
#* 202_type_extension.pss
#********************************************************************
spec_ex_202_type_extension='''

enum config_modes_e {UNKNOWN, MODE_A=10, MODE_B=20};
component uart_c {
action configure {
rand config_modes_e mode;
 constraint {mode != UNKNOWN;}
}
}
package additional_config_pkg {
extend enum config_modes_e {MODE_C=30, MODE_D=50}
extend action uart_c::configure {
constraint {mode != MODE_D;}
}
}
'''

#********************************************************************
#* 204_action_type_extension.pss
#********************************************************************
spec_ex_204_action_type_extension='''

component mem_ops_c {
enum mem_block_tag_e {SYS_MEM, A_MEM, B_MEM, DDR};
buffer mem_buff_s {
rand mem_block_tag_e mem_block;
}
pool mem_buff_s mem;
bind mem *;
action memcpy {
input mem_buff_s src_buff;
output mem_buff_s dst_buff;
}
}
package soc_config_pkg {
extend action mem_ops_c::memcpy {
rand int in [1, 2, 4, 8] ta_width; // introducing new attribute
constraint { // layering additional constraint
src_buff.mem_block in [SYS_MEM, A_MEM, DDR];
dst_buff.mem_block in [SYS_MEM, A_MEM, DDR];
ta_width < 4 -> dst_buff.mem_block != A_MEM;
}
}
}
component pss_top {
import soc_config_pkg::*;// explicitly importing the package grants
// access to types and type-members
mem_ops_c mem_ops;
action test {
mem_ops_c::memcpy cpy1, cpy2;
constraint cpy1.ta_width == cpy2.ta_width;// constraining an
// attribute introduced in an extension
activity {
repeat (3) {
parallel { cpy1; cpy2; };
}
}
}
}

'''

#********************************************************************
#* 206_enum_type_extensions.pss
#********************************************************************
spec_ex_206_enum_type_extensions='''

package mem_defs_pkg { // reusable definitions
enum mem_block_tag_e {}; // initially empty
buffer mem_buff_s {
rand mem_block_tag_e mem_block;
}
}
package AB_subsystem_pkg {
import mem_defs_pkg ::*;
extend enum mem_block_tag_e {A_MEM, B_MEM};
}
package soc_config_pkg {
import mem_defs_pkg ::*;
extend enum mem_block_tag_e {SYS_MEM, DDR};
}
component dma_c {
 import mem_defs_pkg::*;
 action mem2mem_xfer {
 input mem_buff_s src_buff;
 output mem_buff_s dst_buff;
 }
}
extend component dma_c {
import AB_subsystem_pkg::*;
// explicitly importing the package grants
import soc_config_pkg::*; // access to enum items
action dma_test {
activity {
do dma_c::mem2mem_xfer with {
src_buff.mem_block == A_MEM;
dst_buff.mem_block == DDR;
};
}
}
}

'''

#********************************************************************
#* 207_type_inheritance_and_overrides.pss
#********************************************************************
spec_ex_207_type_inheritance_and_overrides='''

//<example>
component top {
//</example>

action axi_write_action { /* ... */ };
action xlator_action {
 axi_write_action axi_action;
 axi_write_action other_axi_action;
 activity {
 axi_action; // overridden by instance
 other_axi_action; // overridden by type
 }
};
action axi_write_action_x : axi_write_action { /* ... */};
action axi_write_action_x2 : axi_write_action_x { /* ... */};
action axi_write_action_x3 : axi_write_action_x { /* ... */};
action reg2axi_top {
 override {
 type axi_write_action with axi_write_action_x;
 instance xlator.axi_action with axi_write_action_x2;
 }
 xlator_action xlator;
 activity {
 repeat (10) {
 xlator; // override applies equally to all 10 traversals
 }
 }
};
action reg2axi_top_x : reg2axi_top {
 override {
 instance xlator.axi_action with axi_write_action_x3;
 }
};

//<example>
}
//</example>
'''

#********************************************************************
#* 210_data_instantiation_in_a_component.pss
#********************************************************************
spec_ex_210_data_instantiation_in_a_component='''

component sub_c {
 int base_addr;

 exec init {
 base_addr = 0x1000;
 }
};
component pss_top {
 sub_c s1, s2;

 exec init {
 s1.base_addr = 0x2000;
 }
}
'''

#********************************************************************
#* 212_accessing_component_data_field_from_an_action.pss
#********************************************************************
spec_ex_212_accessing_component_data_field_from_an_action='''

component sub_c {
bit[31:0] base_addr = 0x1000;
action A {
exec body {
// reference base_addr in context component
activate(comp.base_addr + 0x16);
// activate() is an imported function
}
}
}
component pss_top {
sub_c s1, s2;
exec init {
s1.base_addr = 0x1000;
s2.base_addr = 0x2000;
}
action entry {
sub_c::A a;
activity {
repeat (2) {
a; // Runs sub_c::A with 0x1000 as base_addr when
// associated with s1
// Runs sub_c::A with 0x2000 as base_addr when
// associated with s2;
}
}
}
}
'''

#********************************************************************
#* 214_referencing_pss_variables_using_mustache_notation.pss
#********************************************************************
spec_ex_214_referencing_pss_variables_using_mustache_notation='''

component top {
struct S {
rand int b;
}
action A {
rand int a;
rand S s1;
exec body C = """
 printf("a={{a}} s1.b={{s1.b}} a+b={{a+s1.b}}\n");
""";
}
}
'''

#********************************************************************
#* 215_variable_reference_used_to_select_the_function.pss
#********************************************************************
spec_ex_215_variable_reference_used_to_select_the_function='''

component top {
action A {
rand bit[1:0] func_id;
rand bit[3:0] a;
exec body C = """
 func_{{func_id}}({{a}});
""";
}
}
'''

#********************************************************************
#* 216_declaring_a_random_func_id_variable_that_identifies_a_c_function_to_call.pss
#********************************************************************
spec_ex_216_declaring_a_random_func_id_variable_that_identifies_a_c_function_to_call='''

component top {
action A {
rand bit[1:0] func_id;
rand bit[3:0] a;
exec body C = """
 func_{{func_id}}({{a}});
""";
}
}
'''

#********************************************************************
#* 217_allowing_programmatic_declaration_of_a_target_variable_declaration.pss
#********************************************************************
spec_ex_217_allowing_programmatic_declaration_of_a_target_variable_declaration='''

enum obj_type_e {my_int8,my_int16,my_int32,my_int64};
function string get_unique_obj_name();
import solve function get_unique_obj_name;

buffer mem_buff_s {
 rand obj_type_e obj_type;
 string obj_name;

 exec post_solve {
 obj_name = get_unique_obj_name();
 }

 // declare an object in global space
 exec declaration C = """
 static {{obj_type}} {{obj_name}};
 """;
};
'''

#********************************************************************
#* 218_pi_method.pss
#********************************************************************
spec_ex_218_pi_method='''

package generic_methods {
 function int compute_value(
int val,
output int out_val);
}
'''

#********************************************************************
#* 220_function_availability.pss
#********************************************************************
spec_ex_220_function_availability='''

package external_functions_pkg {

 function bit[31:0] alloc_addr(bit[31:0] size);

 function void transfer_mem(
 bit[31:0] src, bit[31:0] dst, bit[31:0] size
 );
}
package pregen_tests_pkg {

 import solve function external_functions_pkg::alloc_addr;

 import target function external_functions_pkg::transfer_mem;

}
'''

#********************************************************************
#* 222_explicit_specification_of_the_implementation_language.pss
#********************************************************************
spec_ex_222_explicit_specification_of_the_implementation_language='''

package known_c_methods {
import C function generic_methods::compute_expected_value;
}
'''

#********************************************************************
#* 224_calling_pi_functions.pss
#********************************************************************
spec_ex_224_calling_pi_functions='''

package external_functions_pkg {

 function bit[31:0] alloc_addr(bit[31:0] size);

 function void transfer_mem(
 bit[31:0] src, bit[31:0] dst, bit[31:0] size
 );

buffer mem_segment_s {
 rand bit[31:0] size;
 bit[31:0] addr;

 constraint size in [8..4096];

 exec post_solve {
 addr = alloc_addr(size);
 }
 }
}

component mem_xfer {
 import external_functions_pkg::*;

 action xfer_a {
 input mem_segment_s in_buff;
 output mem_segment_s out_buff;

 constraint in_buff.size == out_buff.size;

 exec body {
 transfer_mem(in_buff.addr, out_buff.addr, in_buff.size);
 }
 }
}
'''

#********************************************************************
#* 226_reactive_control_flow.pss
#********************************************************************
spec_ex_226_reactive_control_flow='''

component my_ip_c {
 function int sample_DUT_state();
 import target C function sample_DUT_state;
 // specify mapping to target C function by that same name
 action check_state {
 int curr_val;
 exec body {
 curr_val = comp.sample_DUT_state();
 // value only known during execution on target platform
 }
 };
 action A { };
 action B { };
 action my_test {
 check_state cs;
 activity {
 repeat {
 cs;
 if (cs.curr_val % 2 == 0) {
 do A;
 } else {
 do B;
 }
 } while (cs.curr_val < 10);
 }
 };
};
'''

#********************************************************************
#* 228_target_template_function_implementation.pss
#********************************************************************
spec_ex_228_target_template_function_implementation='''

package thread_ops_pkg {
 function void do_stw(bit[31:0] val, bit[31:0] vaddr);
}
package thread_ops_asm_pkg {
 target ASM function void do_stw(bit[31:0] val, bit[31:0] vaddr) = """
 loadi RA {{val}}
 store RA {{vaddr}}
 """;
}
'''

#********************************************************************
#* 230_import_class.pss
#********************************************************************
spec_ex_230_import_class='''

import class base {
 void base_method();
}
import class ext : base {
 void ext_method();
}
'''

#********************************************************************
#* 236_export_action.pss
#********************************************************************
spec_ex_236_export_action='''

component comp {

 action A1 {
 rand bit mode;
 rand bit[31:0] val;

 constraint {
 if (mode!=0) {
 val in [0..10];
 } else {
 val in [10..100];
 }
 }
 }

}
package pkg {
 // Export A1, providing a mapping to field 'mode'
 export target comp::A1(bit mode);
}
'''

#********************************************************************
#* 240_conditional_processing_static_if.pss
#********************************************************************
spec_ex_240_conditional_processing_static_if='''

package config_pkg {
 const bool PROTOCOL_VER_1_2 = false;
}

//<example>
component top {
//</example>
compile if (config_pkg::PROTOCOL_VER_1_2) {
 action new_flow {
 activity { /* ... */ }
 }
} else {
 action old_flow {
 activity { /* ... */ }
 }
}

//<example>
}
//</example>
'''

#********************************************************************
#* 241_compile_has.pss
#********************************************************************
spec_ex_241_compile_has='''

package config_pkg {
}

//<example>
component top {
//</example>

compile if (compile has(config_pkg::PROTOCOL_VER_1_2) 
    && config_pkg::PROTOCOL_VER_1_2) {
 action new_flow {
   activity { /* ... */ }
 }
} else {
 action old_flow {
 	activity { /* ... */}
 }
 
}

//<example>
}
//</example>

'''

#********************************************************************
#* 242_circular_dependency.pss
#********************************************************************
spec_ex_242_circular_dependency='''

compile if (compile has(FIELD2)) {
 static const int FIELD1 = 1;
}
compile if (compile has (FIELD1)) {
 static const int FIELD2 = 2;
}
'''

#********************************************************************
#* 243_compile_assert.pss
#********************************************************************
spec_ex_243_compile_assert='''

compile if (compile has(FIELD2)) {
 static const int FIELD1 = 1;
}

compile if (compile has (FIELD1)) {
 static const int FIELD2 = 2;
}

compile assert(compile has(FIELD1), "FIELD1 not found");
'''

