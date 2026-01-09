'use client'
import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouter } from 'next/navigation'
import cn from 'classnames'
import Button from '@/app/components/base/button'
import Toast from '@/app/components/base/toast'
import Input from '@/app/components/base/input'
import { validPassword } from '@/config'
import type { MailRegisterResponse } from '@/service/use-common'
import { useMailRegister } from '@/service/use-common'

const SignUpForm = () => {
  const { t } = useTranslation()
  const router = useRouter()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [invitationCode, setInvitationCode] = useState('')
  const [workspaceName, setWorkspaceName] = useState('')
  const { mutateAsync: register, isPending } = useMailRegister()

  const showErrorMessage = useCallback((message: string) => {
    Toast.notify({
      type: 'error',
      message,
    })
  }, [])

  const valid = useCallback(() => {
    if (!invitationCode.trim()) {
      showErrorMessage(t('error.invitationCodeEmpty', { ns: 'login' }) || '邀请码不能为空')
      return false
    }
    if (invitationCode !== 'njupt2025') {
      showErrorMessage(t('invalidInvitationCode', { ns: 'login' }) || '邀请码无效')
      return false
    }
    if (!email.trim()) {
      showErrorMessage(t('error.emailEmpty', { ns: 'login' }))
      return false
    }
    if (!workspaceName.trim()) {
      showErrorMessage(t('error.workspaceNameEmpty', { ns: 'login' }) || '工作空间名称不能为空')
      return false
    }
    if (!password.trim()) {
      showErrorMessage(t('error.passwordEmpty', { ns: 'login' }))
      return false
    }
    if (!validPassword.test(password)) {
      showErrorMessage(t('error.passwordInvalid', { ns: 'login' }))
      return false
    }
    if (password !== confirmPassword) {
      showErrorMessage(t('account.notEqual', { ns: 'common' }))
      return false
    }
    return true
  }, [email, password, confirmPassword, invitationCode, workspaceName, showErrorMessage, t])

  const handleSubmit = useCallback(async () => {
    if (!valid())
      return
    try {
      const res = await register({
        email,
        new_password: password,
        password_confirm: confirmPassword,
        invitation_code: invitationCode,
        workspace_name: workspaceName,
      })
      const { result } = res as MailRegisterResponse
      if (result === 'success') {
        Toast.notify({
          type: 'success',
          message: t('api.actionSuccess', { ns: 'common' }),
        })
        router.replace('/apps')
      }
    }
    catch (error) {
      console.error(error)
    }
  }, [email, password, valid, confirmPassword, invitationCode, workspaceName, register, router, t])

  return (
    <div className={
      cn(
        'flex w-full grow flex-col items-center justify-center',
        'px-6',
        'md:px-[108px]',
      )
    }>
      <div className='flex flex-col md:w-[400px]'>
        <div className="mx-auto w-full">
          <h2 className="title-4xl-semi-bold text-text-primary">
            {t('signup.createAccount', { ns: 'login' }) || '注册'}
          </h2>
          <p className='body-md-regular mt-2 text-text-secondary'>
            {t('signup.signUpTip', { ns: 'login' }) || '使用邀请码注册账户'}
          </p>
        </div>

        <div className="mx-auto mt-6 w-full">
          <div>
            {/* Invitation Code */}
            <div className='mb-5'>
              <label htmlFor="invitationCode" className="system-md-semibold my-2 text-text-secondary">
                {t('invitationCode', { ns: 'login' }) || '邀请码'}
              </label>
              <div className='relative mt-1'>
                <Input
                  id="invitationCode"
                  type='text'
                  value={invitationCode}
                  onChange={e => setInvitationCode(e.target.value)}
                  placeholder={t('invitationCodePlaceholder', { ns: 'login' }) || '请输入邀请码'}
                />
              </div>
            </div>
            {/* Email */}
            <div className='mb-5'>
              <label htmlFor="email" className="system-md-semibold my-2 text-text-secondary">
                {t('email', { ns: 'login' })}
              </label>
              <div className='relative mt-1'>
                <Input
                  id="email"
                  type='text'
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder={t('emailPlaceholder', { ns: 'login' }) || '请输入邮箱'}
                />
              </div>
            </div>
            {/* Workspace Name */}
            <div className='mb-5'>
              <label htmlFor="workspaceName" className="system-md-semibold my-2 text-text-secondary">
                {t('signup.workspaceName', { ns: 'login' }) || '工作空间名称 (用户名)'}
              </label>
              <div className='relative mt-1'>
                <Input
                  id="workspaceName"
                  type='text'
                  value={workspaceName}
                  onChange={e => setWorkspaceName(e.target.value)}
                  placeholder={t('signup.workspaceNamePlaceholder', { ns: 'login' }) || '请输入工作空间名称'}
                />
              </div>
            </div>
            {/* Password */}
            <div className='mb-5'>
              <label htmlFor="password" className="system-md-semibold my-2 text-text-secondary">
                {t('account.newPassword', { ns: 'common' })}
              </label>
              <div className='relative mt-1'>
                <Input
                  id="password"
                  type='password'
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder={t('passwordPlaceholder', { ns: 'login' }) || ''}
                />

              </div>
              <div className='body-xs-regular mt-1 text-text-secondary'>{t('error.passwordInvalid', { ns: 'login' })}</div>
            </div>
            {/* Confirm Password */}
            <div className='mb-5'>
              <label htmlFor="confirmPassword" className="system-md-semibold my-2 text-text-secondary">
                {t('account.confirmPassword', { ns: 'common' })}
              </label>
              <div className='relative mt-1'>
                <Input
                  id="confirmPassword"
                  type='password'
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder={t('confirmPasswordPlaceholder', { ns: 'login' }) || ''}
                />
              </div>
            </div>
            <div>
              <Button
                variant='primary'
                className='w-full'
                onClick={handleSubmit}
                disabled={isPending || !email || !password || !confirmPassword || !invitationCode || !workspaceName}
              >
                {t('signup.createAccount', { ns: 'login' }) || '创建账户'}
              </Button>
            </div>
            <div className="mt-4 text-center">
              <span className="text-text-secondary text-sm">
                {t('signup.haveAccount', { ns: 'login' }) || '已有账户？'}
              </span>
              <a href="/signin" className="text-primary-600 text-sm ml-1 font-medium">
                {t('signup.signIn', { ns: 'login' }) || '登录'}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SignUpForm
