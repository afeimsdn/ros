#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2009, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

## ROS message source code generation for C++
## 
## Converts ROS .msg files in a package into C++ source code implementations.

import roslib; roslib.load_manifest('roscpp')

import sys
import os
import traceback

# roslib.msgs contains the utilities for parsing .msg specifications. It is meant to have no rospy-specific knowledge
import roslib.msgs 
import roslib.packages
import roslib.gentools

from cStringIO import StringIO

MSG_TYPE_TO_CPP = {'byte': 'int8_t', 'char': 'uint8_t',
                   'bool': 'uint8_t',
                   'uint8': 'uint8_t', 'int8': 'int8_t', 
                   'uint16': 'uint16_t', 'int16': 'int16_t', 
                   'uint32': 'uint32_t', 'int32': 'int32_t',
                   'uint64': 'uint64_t', 'int64': 'int64_t',
                   'float32': 'float',
                   'float64': 'double',
                   'string': 'std::string',
                   'time': 'ros::Time',
                   'duration': 'ros::Duration'}

def msg_type_to_cpp(type):
    (base_type, is_array, array_len) = roslib.msgs.parse_type(type)
    cpp_type = None
    if (roslib.msgs.is_builtin(base_type)):
        cpp_type = MSG_TYPE_TO_CPP[base_type]
    elif (len(base_type.split('/')) == 1):
        if (roslib.msgs.is_header_type(base_type)):
            cpp_type = "roslib::Header"
        else:
            cpp_type = base_type
    else:
        pkg = base_type.split('/')[0]
        msg = base_type.split('/')[1]
        cpp_type = '%s::%s'%(pkg, msg)
        
    if (is_array):
        if (array_len is None):
            return 'std::vector<%s>'%(cpp_type)
        else:
            return 'boost::array<%s, %s>'%(cpp_type, array_len)
    else:
        return cpp_type

def write_begin(s, pkg, msg, file):
    s.write("/* Auto-generated by genmsg_cpp for file %s */\n"%(file))
    s.write('#ifndef %s_%s_H\n'%(pkg.upper(), msg.upper()))
    s.write('#define %s_%s_H\n'%(pkg.upper(), msg.upper()))
    
def write_includes(s, spec):
    s.write('#include <string>\n')
    s.write('#include <vector>\n')
    s.write('#include "ros/serialization.h"\n')
    s.write('#include "ros/builtin_message_traits.h"\n')
    s.write('#include "ros/message.h"\n')
    s.write('#include "ros/time.h"\n\n')
    
    fields = spec.fields()
    for (type, name) in fields:
        (base_type, is_array, array_len) = roslib.msgs.parse_type(type)
        if (not roslib.msgs.is_builtin(base_type)):
            if (roslib.msgs.is_header_type(base_type)):
                s.write('#include "roslib/Header.h"\n')
            else:
                s.write('#include "%s.h"\n'%(base_type))
                
    s.write('\n')
    
def write_struct(s, spec, pkg, msg):
    s.write('struct %s : public ros::Message\n{\n'%(msg))
    
    write_constructor(s, msg, spec)
    write_members(s, spec)
    write_constants(s, spec)
    write_deprecated_member_functions(s, spec, pkg, msg)
    
    cpp_msg = '%s::%s'%(pkg, msg)
    s.write('  typedef boost::shared_ptr<%s> Ptr;\n'%(cpp_msg))
    s.write('  typedef boost::shared_ptr<%s const> ConstPtr;\n'%(cpp_msg))
    s.write('}; // struct %s\n'%(msg))
    s.write('typedef boost::shared_ptr<%s> %sPtr;\n'%(cpp_msg, msg))
    s.write('typedef boost::shared_ptr<%s const> %sConstPtr;\n'%(cpp_msg, msg))
    
def write_struct_bodies(s, spec, pkg, msg):
    pass
    
def write_end(s, pkg, msg):
    s.write('#endif // %s_%s_H\n'%(pkg.upper(), msg.upper()))

def default_value(type):
    if type in ['byte', 'int8', 'int16', 'int32', 'int64',
                'char', 'uint8', 'uint16', 'uint32', 'uint64']:
        return '0'
    elif type in ['float32', 'float64']:
        return '0.0'
    elif type == 'bool':
        return 'false'
        
    return ""

def write_constructor(s, msg, spec):
    s.write('  %s()\n'%(msg))
    
    fields = spec.fields()
    i = 0
    for (type, name) in fields:
        (base_type, is_array, array_len) = roslib.msgs.parse_type(type)
        if (is_array):
            continue
        
        if (i == 0):
            s.write('  : ')
        else:
            s.write('  , ')
            
        s.write('  %s(%s)\n'%(name, default_value(base_type)))
        i = i + 1
        
    s.write('  {\n')
    for (type, name) in fields:
        (base_type, is_array, array_len) = roslib.msgs.parse_type(type)
        if (not is_array or array_len is None):
            continue
        
        val = default_value(base_type)
        if (len(val) > 0):
            s.write('    %s.assign(%s);\n'%(name, val))
    s.write('  }\n\n')

def write_member(s, type, name):
    cpp_type = msg_type_to_cpp(type)
    s.write('  typedef %s _%s_type;\n'%(cpp_type, name))
    s.write('  %s %s;\n\n'%(cpp_type, name))

def write_members(s, spec):
    [write_member(s, type, name) for (type, name) in spec.fields()]
        
def write_constant(s, constant):
    if not constant.type in ['byte', 'int8', 'int16', 'int32', 'int64',
                'char', 'uint8', 'uint16', 'uint32', 'uint64',
                'float32', 'float64']:
        raise ValueError('%s not supported as a constant'%(constant.type))
    
    s.write('  static const %s %s = %s;\n'%(msg_type_to_cpp(constant.type), constant.name, constant.val))
        
def write_constants(s, spec):
    [write_constant(s, constant) for constant in spec.constants]
    s.write('\n')
        
def is_fixed_length(spec, package):
    types = []
    fields = spec.fields()
    for (type, name) in fields:
        (base_type, is_array, array_len) = roslib.msgs.parse_type(type)
        if (is_array and array_len is None):
            return False
        
        if (base_type == 'string'):
            return False
        
        if (not roslib.msgs.is_builtin(base_type)):
            types.append(base_type)
            
    types = set(types)
    for type in types:
        (pkg, name) = roslib.names.package_resource_name(type)
        pkg = pkg or package # convert '' to package
        (_, new_spec) = roslib.msgs.load_by_type(type, pkg)
        if (not is_fixed_length(new_spec, pkg)):
            return False
        
    return True
    
def write_deprecated_member_functions(s, spec, pkg, msg):
    cpp_msg = '%s::%s'%(pkg, msg)
    s.write('  virtual const std::string __getDataType() const { return ros::message_traits::datatype<%s>(); }\n'%(cpp_msg))
    s.write('  virtual const std::string __getMD5Sum() const { return ros::message_traits::md5sum<%s>(); }\n'%(cpp_msg))
    s.write('  virtual const std::string __getMessageDefinition() const { return ros::message_traits::definition<%s>(); }\n'%(cpp_msg))
    s.write('  virtual uint32_t serializationLength() const { return ros::serialization::Serializer<%s>::serializedLength(*this); }\n'%(cpp_msg))
    s.write('  virtual uint8_t *serialize(uint8_t *write_ptr, uint32_t seq) const { ros::serialization::Buffer b(write_ptr, 1000000000); b = ros::serialization::Serializer<%s>::write(b, *this); return b.data; }\n'%(cpp_msg))
    s.write('  virtual uint8_t *deserialize(uint8_t *read_ptr) { ros::serialization::Buffer b(read_ptr, 1000000000); b = ros::serialization::Serializer<%s>::read(b, *this); return b.data; }\n\n'%(cpp_msg))

def write_traits_declarations(s, spec, pkg, msg):
    cpp_msg = '%s::%s'%(pkg, msg)
    s.write('namespace ros\n{\n')
    s.write('namespace message_traits\n{\n')
    s.write('template<> inline const char* md5sum<%s>();\n'%(cpp_msg))
    s.write('template<> inline const char* datatype<%s>();\n'%(cpp_msg))
    s.write('template<> inline const char* definition<%s>();\n'%(cpp_msg))
    s.write('} // namespace message_traits\n')
    s.write('} // namespace ros\n\n')

def compute_full_text_escaped(gen_deps_dict):
    """
    Same as roslib.gentools.compute_full_text, except that the
    resulting text is escaped to be safe for C++ double quotes

    @param get_deps_dict: dictionary returned by get_dependencies call
    @type  get_deps_dict: dict
    @return: concatenated text for msg/srv file and embedded msg/srv types. Text will be escaped for double quotes
    @rtype: str
    """
    definition = roslib.gentools.compute_full_text(gen_deps_dict)
    lines = definition.split('\n')
    s = StringIO()
    for line in lines:
        line.replace('\\', '\\\\')
        line.replace('"', '\\"')
        s.write('"%s\\n"\n'%(line))
        
    val = s.getvalue()
    s.close()
    return val

def write_traits_bodies(s, spec, pkg, msg):
    # generate dependencies dictionary
    gendeps_dict = roslib.gentools.get_dependencies(spec, pkg, compute_files=False)
    md5sum = roslib.gentools.compute_md5(gendeps_dict)
    full_text = compute_full_text_escaped(gendeps_dict)
    
    cpp_msg = '%s::%s'%(pkg, msg)
    s.write('namespace ros\n{\n')
    s.write('namespace message_traits\n{\n')
    s.write('template<> inline const char* md5sum<%s>() { return "%s"; }\n'%(cpp_msg, md5sum))
    s.write('template<> inline const char* datatype<%s>() { return "%s/%s"; }\n'%(cpp_msg, pkg, msg))
         
    s.write('template<> inline const char* definition<%s>()\n{\n  return\n'%(cpp_msg))
    s.write(full_text);
    s.write(';\n}\n\n')
    
    if (spec.has_header()):
        s.write('template<> struct HasHeader<%s> : public TrueType {};\n'%(cpp_msg))
        s.write('template<> inline roslib::Header* getHeader(%s& m) { return &m.header; }\n'%(cpp_msg))
        
    if (is_fixed_length(spec, pkg)):
        s.write('template<> struct IsFixedSize<%s> : public TrueType {};\n'%(cpp_msg))
        
    s.write('\n')
        
    s.write('} // namespace message_traits\n')
    s.write('} // namespace ros\n\n')

def write_serialization_declarations(s, spec, pkg, msg):
    cpp_msg = '%s::%s'%(pkg, msg)
    
    s.write('namespace ros\n{\n')
    s.write('namespace serialization\n{\n')
    s.write('template<> struct Serializer<%s>\n{\n'%(cpp_msg))
    s.write('  inline static Buffer write(Buffer buffer, const %s& m);\n'%(cpp_msg))
    s.write('  inline static Buffer read(Buffer buffer, %s& m);\n'%(cpp_msg))
    s.write('  inline static uint32_t serializedLength(const %s& m);\n'%(cpp_msg))
    s.write('};\n')
    s.write('} // namespace serialization\n')
    s.write('} // namespace ros\n\n')
    
def write_serialization_bodies(s, spec, pkg, msg):
    cpp_msg = '%s::%s'%(pkg, msg)
    fields = spec.fields()
    
    s.write('namespace ros\n{\n')
    s.write('namespace serialization\n{\n\n')
    
    s.write('inline Buffer Serializer<%s>::write(Buffer buffer, const %s& m)\n{\n'%(cpp_msg, cpp_msg))
    for (type, name) in fields:
        s.write('  buffer = serialize(buffer, m.%s);\n'%(name))
    s.write('  return buffer;\n}\n\n')
    
    s.write('inline Buffer Serializer<%s>::read(Buffer buffer, %s& m)\n{\n'%(cpp_msg, cpp_msg))
    for (type, name) in fields:
        s.write('  buffer = deserialize(buffer, m.%s);\n'%(name))
    s.write('  return buffer;\n}\n\n')
    
    s.write('inline uint32_t Serializer<%s>::serializedLength(const %s& m)\n{\n'%(cpp_msg, cpp_msg))
    s.write('  uint32_t size = 0;\n');
    for (type, name) in fields:
        s.write('  size += serializationLength(m.%s);\n'%(name))
    s.write('  return size;\n}\n\n')
        
    s.write('} // namespace serialization\n')
    s.write('} // namespace ros\n\n')

def generate(msg_path):
    (package_dir, package) = roslib.packages.get_dir_pkg(msg_path)
    (name, spec) = roslib.msgs.load_from_file(msg_path)
    
    s = StringIO()  
    write_begin(s, package, name, msg_path)
    write_includes(s, spec)
    
    s.write('namespace %s { struct %s; }\n\n' %(package, name))
    write_traits_declarations(s, spec, package, name)
    write_serialization_declarations(s, spec, package, name)
    s.write('namespace %s\n{\n'%(package))
    write_struct(s, spec, package, name)
    write_struct_bodies(s, spec, package, name)
    s.write('} // namespace %s\n\n'%(package))
    write_traits_bodies(s, spec, package, name)
    write_serialization_bodies(s, spec, package, name)
    write_end(s, package, name)
    
    output_dir = '%s/msg/cpp/%s'%(package_dir, package)
    if (not os.path.exists(output_dir)):
        os.makedirs(output_dir)
        
    f = open('%s/%s.h'%(output_dir, name), 'w')
    print >> f, s.getvalue()
    
    s.close()

def generate_messages(argv):
    for arg in argv[1:]:
        generate(arg)

if __name__ == "__main__":
    roslib.msgs.set_verbose(False)
    generate_messages(sys.argv)
