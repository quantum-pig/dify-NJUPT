'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { useTranslation } from 'react-i18next'
import { RiShieldCheckLine, RiShieldCrossLine, RiLockPasswordLine } from '@remixicon/react'
import Button from '@/app/components/base/button'
import Toast from '@/app/components/base/toast'
import { fetchAdminUsers, banUser, unbanUser, resetUserPassword } from '@/service/common'
import Avatar from '@/app/components/base/avatar'
import { useFormatTimeFromNow } from '@/hooks/use-format-time-from-now'

type AdminUser = {
  id: string
  name: string
  email: string
  status: string
  created_at: string
  last_login_at: string | null
  initialized_at: string | null
}

const AdminManagerPage = () => {
  const { t } = useTranslation()
  const { formatTimeFromNow } = useFormatTimeFromNow()
  const { data, mutate } = useSWR(
    {
      url: '/admin/users',
      params: {},
    },
    fetchAdminUsers,
  )
  const users = data?.users || []

  const handleBan = async (userId: string) => {
    try {
      await banUser({ url: `/admin/users/${userId}/ban`, body: {} })
      Toast.notify({
        type: 'success',
        message: t('common.api.actionSuccess'),
      })
      mutate()
    } catch (error) {
      Toast.notify({
        type: 'error',
        message: t('common.api.actionFailed'),
      })
    }
  }

  const handleUnban = async (userId: string) => {
    try {
      await unbanUser({ url: `/admin/users/${userId}/unban`, body: {} })
      Toast.notify({
        type: 'success',
        message: t('common.api.actionSuccess'),
      })
      mutate()
    } catch (error) {
      Toast.notify({
        type: 'error',
        message: t('common.api.actionFailed'),
      })
    }
  }

  const handleResetPassword = async (userId: string) => {
    try {
      await resetUserPassword({ url: `/admin/users/${userId}/reset-password`, body: {} })
      Toast.notify({
        type: 'success',
        message: t('common.api.actionSuccess') || '密码已重置为 njupt2025',
      })
      mutate()
    } catch (error) {
      Toast.notify({
        type: 'error',
        message: t('common.api.actionFailed'),
      })
    }
  }

  return (
    <div className='flex flex-col'>
      <div className='mb-4 system-md-semibold text-text-secondary'>
        {t('common.admin.userManagement') || '用户管理'}
      </div>
      <div className='overflow-visible lg:overflow-visible'>
        <div className='flex min-w-[480px] items-center border-b border-divider-regular py-[7px]'>
          <div className='system-xs-medium-uppercase grow px-3 text-text-tertiary'>{t('common.members.name')}</div>
          <div className='system-xs-medium-uppercase w-[120px] shrink-0 text-text-tertiary'>{t('common.members.email') || '邮箱'}</div>
          <div className='system-xs-medium-uppercase w-[120px] shrink-0 text-text-tertiary'>{t('common.members.status') || '状态'}</div>
          <div className='system-xs-medium-uppercase w-[120px] shrink-0 text-text-tertiary'>{t('common.members.lastActive')}</div>
          <div className='system-xs-medium-uppercase w-[200px] shrink-0 px-3 text-text-tertiary'>{t('common.members.action') || '操作'}</div>
        </div>
        <div className='relative min-w-[480px]'>
          {users.map((user: AdminUser) => (
            <div key={user.id} className='flex border-b border-divider-subtle'>
              <div className='flex grow items-center px-3 py-2'>
                <Avatar avatar={''} size={24} className='mr-2' name={user.name} />
                <div className='system-sm-medium text-text-secondary'>{user.name}</div>
              </div>
              <div className='system-sm-regular flex w-[120px] shrink-0 items-center py-2 text-text-secondary'>{user.email}</div>
              <div className='system-sm-regular flex w-[120px] shrink-0 items-center py-2 text-text-secondary'>
                {user.status === 'closed' || user.status === 'banned' ? (
                  <span className='system-xs-medium text-text-warning'>{t('common.members.banned') || '已封禁'}</span>
                ) : (
                  <span className='system-xs-medium text-text-success'>{t('common.members.active') || '正常'}</span>
                )}
              </div>
              <div className='system-sm-regular flex w-[120px] shrink-0 items-center py-2 text-text-secondary'>
                {user.last_login_at ? formatTimeFromNow(new Date(user.last_login_at).getTime()) : '-'}
              </div>
              <div className='flex w-[200px] shrink-0 items-center gap-2 px-3'>
                {user.status === 'closed' || user.status === 'banned' ? (
                  <Button
                    variant='primary'
                    size='small'
                    onClick={() => handleUnban(user.id)}
                  >
                    <RiShieldCheckLine className='mr-1 h-4 w-4' />
                    {t('common.members.unban') || '解封'}
                  </Button>
                ) : (
                  <Button
                    variant='warning'
                    size='small'
                    onClick={() => handleBan(user.id)}
                  >
                    <RiShieldCrossLine className='mr-1 h-4 w-4' />
                    {t('common.members.ban') || '封禁'}
                  </Button>
                )}
                <Button
                  variant='secondary'
                  size='small'
                  onClick={() => handleResetPassword(user.id)}
                >
                  <RiLockPasswordLine className='mr-1 h-4 w-4' />
                  {t('common.members.resetPassword') || '重置密码'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default AdminManagerPage

