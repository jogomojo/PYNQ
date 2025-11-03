#ifndef XRFCLK_H
#define XRFCLK_H

#include <iostream>
#include <vector>
#include <string>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <cstring>
#include <algorithm>
#include <fcntl.h> 
#include <unistd.h> 
#include <cerrno>

class XRFCLK
{
private:
    // Device structures
    struct LmkDevice {
        std::string spi_device;
        std::string compatible;
        uint32_t num_bytes;
    };
    
    struct LmxDevice {
        std::string spi_device;
        std::string compatible;
    };
    
    // Member variables
    std::vector<LmkDevice> lmk_devices_;
    std::vector<LmxDevice> lmx_devices_;
    bool devices_initialized_;
    
    // Private helper methods
    std::string getSpidevPath(const std::filesystem::path& dev);
    void spidevBind(const std::filesystem::path& dev);
    std::string readFile(const std::filesystem::path& filepath);
    std::vector<uint8_t> readBinaryFile(const std::filesystem::path& filepath);
    void findDevices();

public:
    XRFCLK();
    ~XRFCLK();

    // Get device names for client validation
    std::pair<std::string, std::string> getDeviceNames();
    
    void writeLmkRegs(const std::vector<uint32_t>& reg_vals);
    void writeLmxRegs(const std::vector<uint32_t>& reg_vals);
};

#endif // XRFCLK_H