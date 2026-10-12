/*
 * PtrMap.h
 *
 * Copyright 2026 Matthew Ballance and Contributors
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
 */
#pragma once
#include <cstdint>
#include <utility>
#include <vector>

namespace pssp {
namespace lint {
namespace util {

/**
 * A map from non-null pointers to small values, for the library's per-node
 * indexes (lint-core-plan C8). Open addressing with linear probing in one
 * array: an index over every node of a model is one allocation, not one per
 * node, so it is built, read and freed without the allocator in the loop.
 * No erase. Null is the empty-slot marker and is never a key.
 */
template <class V> class PtrMap {
public:
    PtrMap() { }

    /** The value for `k`, or null. */
    const V *find(const void *k) const {
        if (m_size == 0) {
            return nullptr;
        }
        for (size_t i=slot(k); ; i=(i+1) & m_mask) {
            const Entry &e = m_slots[i];
            if (e.first == k) {
                return &e.second;
            }
            if (!e.first) {
                return nullptr;
            }
        }
    }

    size_t count(const void *k) const { return find(k) ? 1 : 0; }

    /** Adds `k` -> `v` unless `k` is there; true when it was added. */
    bool emplace(const void *k, const V &v) {
        if ((m_size + 1) * 2 > m_slots.size()) {
            grow();
        }
        for (size_t i=slot(k); ; i=(i+1) & m_mask) {
            Entry &e = m_slots[i];
            if (e.first == k) {
                return false;
            }
            if (!e.first) {
                e.first = k;
                e.second = v;
                m_size++;
                return true;
            }
        }
    }

    size_t size() const { return m_size; }

private:
    using Entry = std::pair<const void *, V>;

    size_t slot(const void *k) const {
        // Fibonacci hashing; the low bits of a pointer are alignment.
        uint64_t h = (reinterpret_cast<uintptr_t>(k) >> 3) * 0x9E3779B97F4A7C15ull;
        return static_cast<size_t>(h >> 20) & m_mask;
    }

    void grow() {
        std::vector<Entry> old;
        old.swap(m_slots);
        size_t n = old.empty() ? 1024 : old.size() * 2;
        m_slots.assign(n, Entry(nullptr, V()));
        m_mask = n - 1;
        m_size = 0;
        for (const Entry &e : old) {
            if (e.first) {
                emplace(e.first, e.second);
            }
        }
    }

    std::vector<Entry>  m_slots;
    size_t              m_mask = 0;
    size_t              m_size = 0;
};

}
}
}
