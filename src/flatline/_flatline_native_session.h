#pragma once

#include <string>
#include <utility>
#include <vector>

#include <nanobind/nanobind.h>

class NativeSession {
   public:
    explicit NativeSession(std::string runtime_data_dir);

    std::vector<std::pair<std::string, std::string>> list_language_compilers() const;
    nanobind::dict decompile_function(const nanobind::dict& request) const;
    void close();

   private:
    std::string runtime_data_dir_;
};
