/**
 * IMarkerCollector.h
 *
 * Copyright 2022 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author: 
 */
#pragma once
#include <cstdint>
#include <memory>
#include "pssp/IMarkerListener.h"

namespace pssp {


class IMarkerCollector;
using IMarkerCollectorUP=std::unique_ptr<IMarkerCollector>;
class IMarkerCollector : public virtual IMarkerListener {
public:

    virtual ~IMarkerCollector() { }

	virtual const std::vector<IMarkerUP> &markers() const = 0;

	// 0 (the default) means unlimited. Only Error-severity markers count
	// against the cap; a collector that has reached it emits one PSS029
	// marker and silently drops further errors (see MarkerCollector::marker).
	virtual void setMaxErrors(int32_t max) = 0;

	virtual bool maxErrorsExceeded() const = 0;

};

}
