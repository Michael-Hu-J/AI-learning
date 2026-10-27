// vars/runTests.groovy — 共享库
def call(String testType, String testDir) {
    stage("${testType}测试") {
        sh "pytest ${testDir} -v --junitxml=reports/${testType}-report.xml"
        junit "reports/${testType}-report.xml"
    }
}

// Jenkinsfile 中使用
runTests("API", "tests/api/")
runTests("UI", "tests/ui/")
