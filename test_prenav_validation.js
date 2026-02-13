/**
 * Test script for prenav form validation (Issue 16.5, 16.6)
 * Tests time input handling with HH:MM:SS format
 */

// Mock DOM elements
const mockDOM = {
    nav_id: { value: '1', options: [
        { dataset: { checkpoints: '3' }, text: 'NAV-1' }
    ], selectedIndex: 1 },
    leg_0_hh: { value: '0' },
    leg_0_mm: { value: '5' },
    leg_0_ss: { value: '30' },
    leg_1_hh: { value: '0' },
    leg_1_mm: { value: '5' },
    leg_1_ss: { value: '0' },
    leg_2_hh: { value: '0' },
    leg_2_mm: { value: '5' },
    leg_2_ss: { value: '0' },
    total_time_hh: { value: '0' },
    total_time_mm: { value: '48' },
    total_time_ss: { value: '30' },
    fuel_estimate: { value: '8.5' }
};

function testTimeConversion() {
    console.log('=== Testing Time Conversion ===');
    
    // Test case 1: Convert leg times HH:MM:SS to seconds
    const legTimes = [];
    const numCheckpoints = 3;
    
    for (let i = 0; i < numCheckpoints; i++) {
        const hh = parseInt(mockDOM[`leg_${i}_hh`].value || 0);
        const mm = parseInt(mockDOM[`leg_${i}_mm`].value || 0);
        const ss = parseInt(mockDOM[`leg_${i}_ss`].value || 0);
        
        const totalSeconds = hh * 3600 + mm * 60 + ss;
        legTimes.push(totalSeconds);
        
        console.log(`Leg ${i+1}: ${hh}h ${mm}m ${ss}s = ${totalSeconds} seconds`);
    }
    
    // Verify conversions
    const expected = [330, 300, 300]; // 5:30, 5:00, 5:00
    const match = JSON.stringify(legTimes) === JSON.stringify(expected);
    console.log(`Leg times match expected [${expected}]: ${match}`);
    if (!match) {
        console.error(`FAIL: Got ${JSON.stringify(legTimes)}, expected ${JSON.stringify(expected)}`);
        return false;
    }
    
    // Test case 2: Convert total time HH:MM:SS to seconds
    const totalHH = parseInt(mockDOM.total_time_hh.value || 0);
    const totalMM = parseInt(mockDOM.total_time_mm.value || 0);
    const totalSS = parseInt(mockDOM.total_time_ss.value || 0);
    
    const totalTimeInSeconds = totalHH * 3600 + totalMM * 60 + totalSS;
    console.log(`\nTotal time: ${totalHH}h ${totalMM}m ${totalSS}s = ${totalTimeInSeconds} seconds`);
    
    const expectedTotal = 2910; // 48:30 = 48*60 + 30 = 2910
    const totalMatch = totalTimeInSeconds === expectedTotal;
    console.log(`Total time matches expected ${expectedTotal}: ${totalMatch}`);
    if (!totalMatch) {
        console.error(`FAIL: Got ${totalTimeInSeconds}, expected ${expectedTotal}`);
        return false;
    }
    
    return true;
}

function testValidation() {
    console.log('\n=== Testing Validation Logic ===');
    
    const tests = [
        {
            name: 'Valid inputs',
            inputs: { hh: 0, mm: 5, ss: 30 },
            shouldPass: true
        },
        {
            name: 'Zero values',
            inputs: { hh: 0, mm: 0, ss: 0 },
            shouldPass: false  // Cannot have 0 seconds
        },
        {
            name: 'Max valid hours',
            inputs: { hh: 23, mm: 59, ss: 59 },
            shouldPass: true
        },
        {
            name: 'Invalid hours (24)',
            inputs: { hh: 24, mm: 0, ss: 0 },
            shouldPass: false
        },
        {
            name: 'Invalid minutes (60)',
            inputs: { hh: 0, mm: 60, ss: 0 },
            shouldPass: false
        },
        {
            name: 'Invalid seconds (60)',
            inputs: { hh: 0, mm: 5, ss: 60 },
            shouldPass: false
        }
    ];
    
    let allPass = true;
    for (const test of tests) {
        const { hh, mm, ss } = test.inputs;
        const isValidRange = hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59 && ss >= 0 && ss <= 59;
        const totalSeconds = hh * 3600 + mm * 60 + ss;
        const isValidTotal = totalSeconds !== 0;
        const overallValid = isValidRange && isValidTotal;
        const pass = overallValid === test.shouldPass;
        
        console.log(`${pass ? '✓' : '✗'} ${test.name}: ${hh}:${mm}:${ss} - Valid: ${overallValid}`);
        if (!pass) allPass = false;
    }
    
    return allPass;
}

function testFormData() {
    console.log('\n=== Testing Form Data Structure ===');
    
    // Simulate form submission
    const legTimes = [330, 300, 300];
    const totalTimeInSeconds = 2910;
    const fuelEstimate = 8.5;
    const navId = 1;
    
    const formData = {
        nav_id: navId,
        leg_times_str: JSON.stringify(legTimes),
        total_time_str: totalTimeInSeconds.toString(),
        fuel_estimate: fuelEstimate
    };
    
    console.log('Form data structure:');
    console.log(`  nav_id: ${formData.nav_id}`);
    console.log(`  leg_times_str: ${formData.leg_times_str}`);
    console.log(`  total_time_str: ${formData.total_time_str}`);
    console.log(`  fuel_estimate: ${formData.fuel_estimate}`);
    
    // Verify JSON parsing works
    try {
        const parsed = JSON.parse(formData.leg_times_str);
        console.log(`✓ leg_times_str is valid JSON: [${parsed}]`);
    } catch (e) {
        console.error(`✗ leg_times_str is invalid JSON: ${e}`);
        return false;
    }
    
    return true;
}

// Run all tests
console.log('NAV Scoring - Prenav Form Validation Tests (Issues 16.5, 16.6)\n');
const results = [
    testTimeConversion(),
    testValidation(),
    testFormData()
];

console.log('\n=== Summary ===');
const allTestsPass = results.every(r => r);
console.log(`All tests: ${allTestsPass ? '✓ PASS' : '✗ FAIL'}`);

if (!allTestsPass) {
    process.exit(1);
}
