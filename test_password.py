from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def test_password_hash_and_verify():
    # 这是专门用于测试的假密码
    password = "example-password-123"

    # 将密码转换成哈希
    hashed = password_hash.hash(password)

    # 保存的内容不应是原始密码
    assert hashed != password

    # 正确密码可以通过验证
    assert password_hash.verify(password, hashed)

    # 错误密码不能通过验证
    assert not password_hash.verify("wrong-password", hashed)