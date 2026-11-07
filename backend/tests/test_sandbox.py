import pytest
from app.services.sandbox import execute_snapshot, available


@pytest.mark.skipif(not available(), reason="Dedicated sandbox image not available")
def test_auth_dependencies_available_without_network_install():
    r=execute_snapshot([{"path":"tests/test_auth.py","content":'''import bcrypt
from jose import jwt
def test_password_and_token_libraries():
    hashed=bcrypt.hashpw(b"classroom-test", bcrypt.gensalt(rounds=4))
    assert bcrypt.checkpw(b"classroom-test", hashed)
    token=jwt.encode({"sub":"student"}, "test-only-local-key", algorithm="HS256")
    assert jwt.decode(token, "test-only-local-key", algorithms=["HS256"])["sub"]=="student"
'''}],"python")
    assert r["status"]=="passed",r


@pytest.mark.skipif(not available(), reason="Dedicated sandbox image not available")
def test_real_sandbox_denies_network_and_host_writes():
    source = """import socket, pathlib, os
import pytest
def test_network_denied():
    with pytest.raises(OSError): socket.create_connection(('1.1.1.1',443),timeout=1)
def test_root_read_only():
    with pytest.raises(OSError): pathlib.Path('/forbidden.txt').write_text('x')
def test_no_secret_or_docker_socket():
    assert 'DATABASE_URL' not in os.environ
    assert 'JWT_SECRET' not in os.environ
    assert not pathlib.Path('/var/run/docker.sock').exists()
"""
    r = execute_snapshot(
        [{"path": "tests/test_isolation.py", "content": source}], "python"
    )
    assert r["status"] == "passed", r
    assert r["total"] == 3


@pytest.mark.skipif(not available(), reason="Dedicated sandbox image not available")
def test_wall_time_limit_and_failed_assertion():
    r = execute_snapshot(
        [
            {
                "path": "tests/test_wait.py",
                "content": "import time\ndef test_wait(): time.sleep(20)",
            }
        ],
        "python",
        time_limit=2,
    )
    assert r["status"] == "timed_out"
    r = execute_snapshot(
        [{"path": "tests/test_fail.py", "content": "def test_failure(): assert False"}],
        "python",
    )
    assert r["status"] == "failed"
    assert r["failed"] == 1


@pytest.mark.skipif(not available(), reason="Dedicated sandbox image not available")
def test_node_and_java_recipes():
    r = execute_snapshot(
        [
            {
                "path": "tests/smoke.test.cjs",
                "content": "const {test}=require('node:test');const assert=require('node:assert');test('sum',()=>assert.equal(2+2,4));",
            }
        ],
        "node",
    )
    assert r["status"] == "passed", r
    r = execute_snapshot(
        [
            {
                "path": "tests/TestMain.java",
                "content": 'public class TestMain { public static void main(String[] args) { if (2+2!=4) throw new AssertionError(); System.out.println("TESTS total=1 passed=1 failed=0"); }}',
            }
        ],
        "java",
    )
    assert r["status"] == "passed", r
