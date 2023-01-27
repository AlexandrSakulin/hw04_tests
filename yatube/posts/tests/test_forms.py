from http import HTTPStatus
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostsFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='test-author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug 2',
            description='Тестовое описание 2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост тестового пользователя в тестовой группе',
        )

    def setUp(self):
        """Создаем клиента и пост."""
        self.auth_client = Client()
        self.auth_client.force_login(self.user)
        self.post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
            group=self.group)

    def test_create_post_form(self):
        """При отправке формы создается новый пост в базе данных.
        После создания происходит редирект на профиль автора.
        """
        post_count = Post.objects.all().count()
        form_data = {
            'text': 'Еще один пост',
            'group': self.group.id
        }
        response = self.auth_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', args=(self.user.username,))
        )
        self.assertEqual(
            Post.objects.all().count(),
            post_count + 1,
            'Пост не сохранен в базу данных!'
        )
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост тестового пользователя в тестовой группе',
                group=self.group
            ).exists())
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост тестового пользователя в тестовой группе',
                author=self.user
            ).exists())

    def test_authorized_user_edit_post(self):
        """Проверка редактирования записи авторизированным клиентом."""
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.user)
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id}
        response = self.auth_client.post(
            reverse(
                'posts:post_edit',
                args=(post.id,)),
            data=form_data,
            follow=True)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(post.id,)))
        post_one = Post.objects.latest('id')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post_one.text, form_data['text'])
        self.assertEqual(post_one.author, self.user)
        self.assertEqual(post_one.group_id, form_data['group'])

    def test_guest_create_post(self):
        """Проверка что неавторизованный юзер
        не сможет создать пост."""
        post_count = Post.objects.count()
        form_fields = {
            'text': 'Тестовый пост контент 2',
            'group': self.group.pk
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_fields,
        )
        redirect = "%s?next=%s" % (
            reverse('users:login'), reverse('posts:post_create')
        )
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), post_count)
